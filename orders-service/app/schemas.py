from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import OrderStatus


class CartCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)


class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CartItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    quantity: int
    price_snapshot: Decimal


class CartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session_id: str
    created_at: datetime
    items: list[CartItemOut]
    total: Decimal


class OrderCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    customer_name: str = Field(min_length=1, max_length=200)
    customer_phone: str = Field(min_length=1, max_length=20)
    customer_email: EmailStr
    delivery_address: str = Field(min_length=1)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    product_name: str
    quantity: int
    price: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_number: str
    customer_name: str
    customer_phone: str
    customer_email: str
    delivery_address: str
    total_amount: Decimal
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
