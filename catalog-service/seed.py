"""Naive idempotent seed: 4 categories + 20 lamp products."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Category, Product


CATEGORIES = [
    ("Светодиодные", "led"),
    ("Галогенные", "halogen"),
    ("Лампы накаливания", "incandescent"),
    ("Энергосберегающие", "cfl"),
]

PRODUCTS = [
    # (category_slug, name, sku, price, stock, watt, socket, image)
    ("led", "LED-лампа Эконом 7W E27", "LED-E27-7", "149.00", 120, 7, "E27", None),
    ("led", "LED-лампа Эконом 9W E27", "LED-E27-9", "179.00", 95, 9, "E27", None),
    ("led", "LED-лампа Эконом 12W E27", "LED-E27-12", "229.00", 80, 12, "E27", None),
    ("led", "LED-лампа Свеча 5W E14", "LED-E14-5", "159.00", 200, 5, "E14", None),
    ("led", "LED-лампа Свеча 7W E14", "LED-E14-7", "189.00", 150, 7, "E14", None),
    ("led", "LED-софит GU10 5W", "LED-GU10-5", "199.00", 90, 5, "GU10", None),
    ("led", "LED-софит GU10 7W", "LED-GU10-7", "239.00", 60, 7, "GU10", None),
    ("led", "LED-лампа Шар 8W E27", "LED-E27-8B", "199.00", 70, 8, "E27", None),
    ("halogen", "Галогенная капсула G4 20W", "HAL-G4-20", "89.00", 50, 20, "G4", None),
    ("halogen", "Галогенная капсула G9 40W", "HAL-G9-40", "119.00", 45, 40, "G9", None),
    ("halogen", "Галоген рефлектор GU10 50W", "HAL-GU10-50", "139.00", 30, 50, "GU10", None),
    ("halogen", "Галоген линейная R7s 100W", "HAL-R7S-100", "169.00", 25, 100, "R7s", None),
    ("incandescent", "Лампа накаливания 40W E27", "INC-E27-40", "39.00", 300, 40, "E27", None),
    ("incandescent", "Лампа накаливания 60W E27", "INC-E27-60", "45.00", 250, 60, "E27", None),
    ("incandescent", "Лампа накаливания 75W E27", "INC-E27-75", "49.00", 180, 75, "E27", None),
    ("incandescent", "Лампа накаливания 100W E27", "INC-E27-100", "55.00", 150, 100, "E27", None),
    ("cfl", "Энергосберегающая 11W E27", "CFL-E27-11", "169.00", 60, 11, "E27", None),
    ("cfl", "Энергосберегающая 15W E27", "CFL-E27-15", "189.00", 55, 15, "E27", None),
    ("cfl", "Энергосберегающая 20W E27", "CFL-E27-20", "219.00", 40, 20, "E27", None),
    ("cfl", "Энергосберегающая 9W E14", "CFL-E14-9", "159.00", 70, 9, "E14", None),
]


def seed(db: Session) -> None:
    cat_by_slug: dict[str, Category] = {}
    for name, slug in CATEGORIES:
        category = Category(name=name, slug=slug)
        db.add(category)
        cat_by_slug[slug] = category
    db.flush()

    for slug, name, sku, price, stock, watt, socket, image in PRODUCTS:
        db.add(
            Product(
                category_id=cat_by_slug[slug].id,
                name=name,
                sku=sku,
                price=Decimal(price),
                stock=stock,
                power_watt=watt,
                socket_type=socket,
                image_url=image,
                description=f"{name}. Цоколь {socket}, мощность {watt} Вт.",
            )
        )
    db.commit()
