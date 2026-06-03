from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# --- auth ---
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str | None = None


# --- products (повторяем контракт catalog-service) ---
class ProductCreate(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=50)
    description: str | None = None
    price: Decimal = Field(ge=0)
    stock: int = Field(ge=0, default=0)
    power_watt: int | None = Field(default=None, ge=0)
    socket_type: str | None = Field(default=None, max_length=20)
    image_url: str | None = Field(default=None, max_length=500)


class ProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, max_length=200)
    sku: str | None = Field(default=None, max_length=50)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    power_watt: int | None = Field(default=None, ge=0)
    socket_type: str | None = Field(default=None, max_length=20)
    image_url: str | None = Field(default=None, max_length=500)


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100)


# --- orders ---
class OrderStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=20)
