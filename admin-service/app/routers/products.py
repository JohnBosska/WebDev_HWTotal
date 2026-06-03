from fastapi import APIRouter, Depends, Query, Response, status

from .. import clients, models, schemas
from ..deps import get_current_user


# Все эндпоинты управления товарами требуют авторизации менеджера.
router = APIRouter(
    prefix="/api/admin",
    tags=["admin: products"],
    dependencies=[Depends(get_current_user)],
)


# --- категории (для выпадающих списков и создания) ---
@router.get("/categories")
def list_categories():
    return clients.catalog.get("/api/categories")


@router.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category(payload: schemas.CategoryCreate):
    return clients.catalog.post("/api/categories", json=payload.model_dump())


# --- товары ---
@router.get("/products")
def list_products(
    category: int | None = Query(default=None),
    sort: str = Query(default="id"),
    order: str = Query(default="asc"),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    params = {"sort": sort, "order": order, "limit": limit, "offset": offset}
    if category is not None:
        params["category"] = category
    return clients.catalog.get("/api/products", params=params)


@router.get("/products/{product_id}")
def get_product(product_id: int):
    return clients.catalog.get(f"/api/products/{product_id}")


@router.post("/products", status_code=status.HTTP_201_CREATED)
def create_product(payload: schemas.ProductCreate):
    body = payload.model_dump()
    body["price"] = float(body["price"])
    return clients.catalog.post("/api/products", json=body)


@router.put("/products/{product_id}")
def update_product(product_id: int, payload: schemas.ProductUpdate):
    body = payload.model_dump(exclude_unset=True)
    if "price" in body and body["price"] is not None:
        body["price"] = float(body["price"])
    return clients.catalog.put(f"/api/products/{product_id}", json=body)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int):
    clients.catalog.delete(f"/api/products/{product_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
