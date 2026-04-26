import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from .config import settings
from .database import Base, SessionLocal, engine
from .models import Category, Product
from .routers import categories, products


logger = logging.getLogger("catalog")
logging.basicConfig(level=logging.INFO)


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


def seed_initial_data() -> None:
    from seed import seed

    with SessionLocal() as db:
        if db.scalar(select(Product).limit(1)) is not None:
            return
        seed(db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        seed_initial_data()
    yield


app = FastAPI(
    title="Catalog Service",
    version="1.0.0",
    description="Микросервис товаров (лампочек) и категорий",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(products.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "catalog"}
