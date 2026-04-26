import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from .database import Base, engine
from .routers import carts, orders


logger = logging.getLogger("orders")
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


@asynccontextmanager
async def lifespan(_: FastAPI):
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Orders Service",
    version="1.0.0",
    description="Микросервис корзин и заказов",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(carts.router)
app.include_router(orders.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "orders"}
