import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from . import models, security
from .config import settings
from .database import Base, SessionLocal, engine
from .routers import auth, orders, products


logger = logging.getLogger("admin")
logging.basicConfig(level=logging.INFO)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def wait_for_db(retries: int = 30, delay: float = 1.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(select(1))
            return
        except OperationalError as exc:
            logger.info("DB not ready (attempt %s/%s): %s", attempt, retries, exc)
            time.sleep(delay)
    raise RuntimeError("Database is not reachable")


def seed_default_admin() -> None:
    with SessionLocal() as db:
        if db.scalar(select(models.AdminUser).limit(1)) is not None:
            return
        user = models.AdminUser(
            username=settings.default_admin_username,
            password_hash=security.hash_password(settings.default_admin_password),
            full_name="Менеджер магазина",
        )
        db.add(user)
        db.commit()
        logger.info("Создан менеджер по умолчанию: %s", settings.default_admin_username)


@asynccontextmanager
async def lifespan(_: FastAPI):
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    if settings.seed_admin_on_startup:
        seed_default_admin()
    yield


app = FastAPI(
    title="Admin Service",
    version="1.0.0",
    description="Микросервис панели управления: авторизация менеджера, "
    "управление товарами и заказами (шлюз к catalog и orders).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "admin"}


# Статика панели управления — отдаётся на корне сервиса (http://localhost:8003/).
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
