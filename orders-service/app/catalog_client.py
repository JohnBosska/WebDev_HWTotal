import httpx
from fastapi import HTTPException, status

from .config import settings


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=settings.catalog_service_url,
        timeout=settings.catalog_request_timeout,
    )


def get_product(product_id: int) -> dict:
    with _client() as c:
        r = c.get(f"/api/products/{product_id}")
    if r.status_code == 404:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product {product_id} not found in catalog")
    if r.status_code >= 400:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"Catalog error: {r.status_code} {r.text}"
        )
    return r.json()


def change_stock(product_id: int, delta: int) -> dict:
    with _client() as c:
        r = c.patch(f"/api/products/{product_id}/stock", json={"delta": delta})
    if r.status_code == 404:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product {product_id} not found in catalog")
    if r.status_code == 409:
        raise HTTPException(status.HTTP_409_CONFLICT, r.json().get("detail", "Stock conflict"))
    if r.status_code >= 400:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"Catalog error: {r.status_code} {r.text}"
        )
    return r.json()
