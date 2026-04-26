import secrets
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import catalog_client, models, schemas
from ..database import get_db
from ..models import OrderStatus


router = APIRouter(prefix="/api/orders", tags=["orders"])


# new -> confirmed -> shipped -> delivered
# в любой момент до shipped допустим переход в cancelled
TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.new: {OrderStatus.confirmed, OrderStatus.cancelled},
    OrderStatus.confirmed: {OrderStatus.shipped, OrderStatus.cancelled},
    OrderStatus.shipped: {OrderStatus.delivered},
    OrderStatus.delivered: set(),
    OrderStatus.cancelled: set(),
}


def _generate_order_number() -> str:
    return "ORD-" + secrets.token_hex(5).upper()


@router.post("", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    cart = db.scalar(select(models.Cart).where(models.Cart.session_id == payload.session_id))
    if not cart or not cart.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cart is empty or not found")

    # 1) резервируем сток через catalog-service (по одной позиции)
    reserved: list[tuple[int, int]] = []
    try:
        for item in cart.items:
            catalog_client.change_stock(item.product_id, -item.quantity)
            reserved.append((item.product_id, item.quantity))
    except HTTPException:
        # откатываем уже зарезервированный сток
        for pid, qty in reserved:
            try:
                catalog_client.change_stock(pid, qty)
            except HTTPException:
                pass
        raise

    # 2) собираем актуальные имена (на всякий случай ещё раз дернем catalog для имени)
    product_names: dict[int, str] = {}
    for pid, _ in reserved:
        try:
            p = catalog_client.get_product(pid)
            product_names[pid] = p["name"]
        except HTTPException:
            product_names[pid] = f"product#{pid}"

    total = sum((i.price_snapshot * i.quantity for i in cart.items), Decimal("0"))

    # 3) создаем заказ
    order_number = _generate_order_number()
    order = models.Order(
        order_number=order_number,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_email=payload.customer_email,
        delivery_address=payload.delivery_address,
        total_amount=total,
        status=OrderStatus.new,
        items=[
            models.OrderItem(
                product_id=i.product_id,
                product_name=product_names.get(i.product_id, f"product#{i.product_id}"),
                quantity=i.quantity,
                price=i.price_snapshot,
            )
            for i in cart.items
        ],
    )
    db.add(order)

    # 4) очищаем корзину
    db.delete(cart)
    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=list[schemas.OrderOut])
def list_orders(
    db: Session = Depends(get_db),
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(models.Order).order_by(models.Order.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(models.Order.status == status_filter)
    stmt = stmt.offset(offset).limit(limit)
    return db.scalars(stmt).all()


@router.get("/{order_number}", response_model=schemas.OrderOut)
def get_order(order_number: str, db: Session = Depends(get_db)):
    order = db.scalar(select(models.Order).where(models.Order.order_number == order_number))
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.patch("/{order_id}/status", response_model=schemas.OrderOut)
def change_status(
    order_id: int,
    payload: schemas.OrderStatusUpdate,
    db: Session = Depends(get_db),
):
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    if payload.status == order.status:
        return order

    allowed = TRANSITIONS.get(order.status, set())
    if payload.status not in allowed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Illegal transition: {order.status.value} -> {payload.status.value}",
        )

    if payload.status == OrderStatus.cancelled:
        for item in order.items:
            try:
                catalog_client.change_stock(item.product_id, item.quantity)
            except HTTPException:
                # товар мог быть удалён; не блокируем отмену заказа
                pass

    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order
