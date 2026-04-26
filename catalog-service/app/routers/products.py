from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db


router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[schemas.ProductOut])
def list_products(
    db: Session = Depends(get_db),
    category: int | None = Query(default=None, description="ID категории"),
    socket_type: str | None = Query(default=None, description="Цоколь, например E27"),
    power_watt: int | None = Query(default=None, description="Мощность, Вт"),
    sort: str = Query(default="id", pattern="^(id|name|price|stock|created_at)$"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(models.Product)
    if category is not None:
        stmt = stmt.where(models.Product.category_id == category)
    if socket_type is not None:
        stmt = stmt.where(models.Product.socket_type == socket_type)
    if power_watt is not None:
        stmt = stmt.where(models.Product.power_watt == power_watt)

    sort_col = getattr(models.Product, sort)
    stmt = stmt.order_by(sort_col.desc() if order == "desc" else sort_col.asc())
    stmt = stmt.offset(offset).limit(limit)
    return db.scalars(stmt).all()


@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product


@router.post("", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    if not db.get(models.Category, payload.category_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Category does not exist")
    product = models.Product(**payload.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "SKU already exists")
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(get_db)
):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and not db.get(models.Category, data["category_id"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Category does not exist")
    for field, value in data.items():
        setattr(product, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "SKU already exists")
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    db.delete(product)
    db.commit()


@router.patch("/{product_id}/stock", response_model=schemas.ProductOut)
def change_stock(
    product_id: int, payload: schemas.StockChange, db: Session = Depends(get_db)
):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    new_stock = product.stock + payload.delta
    if new_stock < 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Not enough stock: have {product.stock}, requested {-payload.delta}",
        )
    product.stock = new_stock
    db.commit()
    db.refresh(product)
    return product
