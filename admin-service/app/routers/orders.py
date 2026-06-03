from fastapi import APIRouter, Depends, Query

from .. import clients, schemas
from ..deps import get_current_user


# Управление заказами — только для авторизованного менеджера.
router = APIRouter(
    prefix="/api/admin/orders",
    tags=["admin: orders"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
def list_orders(
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    params = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status
    return clients.orders.get("/api/orders", params=params)


@router.get("/{order_number}")
def get_order(order_number: str):
    return clients.orders.get(f"/api/orders/{order_number}")


@router.patch("/{order_id}/status")
def change_status(order_id: int, payload: schemas.OrderStatusUpdate):
    return clients.orders.patch(
        f"/api/orders/{order_id}/status", json=payload.model_dump()
    )
