from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import catalog_client, models, schemas
from ..database import get_db


router = APIRouter(prefix="/api/cart", tags=["cart"])


def _serialize(cart: models.Cart) -> dict:
    total = sum((i.price_snapshot * i.quantity for i in cart.items), Decimal("0"))
    return {
        "id": cart.id,
        "session_id": cart.session_id,
        "created_at": cart.created_at,
        "items": cart.items,
        "total": total,
    }


def _get_cart(db: Session, session_id: str) -> models.Cart:
    cart = db.scalar(select(models.Cart).where(models.Cart.session_id == session_id))
    if not cart:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart not found")
    return cart


@router.post("", response_model=schemas.CartOut, status_code=status.HTTP_201_CREATED)
def create_cart(payload: schemas.CartCreate, db: Session = Depends(get_db)):
    cart = models.Cart(session_id=payload.session_id)
    db.add(cart)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Cart for this session already exists")
    db.refresh(cart)
    return _serialize(cart)


@router.get("/{session_id}", response_model=schemas.CartOut)
def get_cart(session_id: str, db: Session = Depends(get_db)):
    return _serialize(_get_cart(db, session_id))


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart(session_id: str, db: Session = Depends(get_db)):
    cart = _get_cart(db, session_id)
    db.delete(cart)
    db.commit()


@router.post("/{session_id}/items", response_model=schemas.CartOut)
def add_item(
    session_id: str, payload: schemas.CartItemAdd, db: Session = Depends(get_db)
):
    cart = _get_cart(db, session_id)
    product = catalog_client.get_product(payload.product_id)
    if product["stock"] < payload.quantity:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Not enough stock: {product['stock']} available"
        )

    existing = next((i for i in cart.items if i.product_id == payload.product_id), None)
    if existing:
        existing.quantity += payload.quantity
    else:
        cart.items.append(
            models.CartItem(
                product_id=payload.product_id,
                quantity=payload.quantity,
                price_snapshot=Decimal(str(product["price"])),
            )
        )
    db.commit()
    db.refresh(cart)
    return _serialize(cart)


@router.patch("/{session_id}/items/{item_id}", response_model=schemas.CartOut)
def update_item(
    session_id: str,
    item_id: int,
    payload: schemas.CartItemUpdate,
    db: Session = Depends(get_db),
):
    cart = _get_cart(db, session_id)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart item not found")

    product = catalog_client.get_product(item.product_id)
    if product["stock"] < payload.quantity:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Not enough stock: {product['stock']} available"
        )

    item.quantity = payload.quantity
    db.commit()
    db.refresh(cart)
    return _serialize(cart)


@router.delete("/{session_id}/items/{item_id}", response_model=schemas.CartOut)
def delete_item(session_id: str, item_id: int, db: Session = Depends(get_db)):
    cart = _get_cart(db, session_id)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart item not found")
    db.delete(item)
    db.commit()
    db.refresh(cart)
    return _serialize(cart)
