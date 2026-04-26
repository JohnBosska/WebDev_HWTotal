# Интернет-магазин лампочек — ДЗ-2 (микросервисы товаров и заказов)

Реализация двух backend-микросервисов из ТЗ:

- **catalog-service** (порт `8001`) — товары (лампочки), категории, остатки.
- **orders-service** (порт `8002`) — корзины, оформление и статусы заказов.

Микросервис панели управления и аутентификация по условию ДЗ-2 пока не делаются.

## Стек

- Python 3.12 + **FastAPI**
- **SQLAlchemy 2** + **psycopg2** + **PostgreSQL 16**
- Pydantic v2 (валидация), `pydantic-settings` (конфигурация из env)
- `httpx` — HTTP-клиент orders → catalog
- **Docker Compose** — оркестрация (PostgreSQL × 2, два сервиса)

## Структура

```
homework2-microservices/
├── docker-compose.yml
├── README.md
├── catalog-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── seed.py                       # 4 категории + 20 ламп (idempotent)
│   ├── database_schema.md
│   ├── postman/catalog_api.postman_collection.json
│   └── app/
│       ├── main.py                   # FastAPI, lifespan, миграции
│       ├── config.py                 # Settings (env)
│       ├── database.py               # engine, sessionmaker
│       ├── models.py                 # Category, Product
│       ├── schemas.py                # Pydantic DTO
│       └── routers/
│           ├── categories.py
│           └── products.py
└── orders-service/
    ├── Dockerfile
    ├── requirements.txt
    ├── database_schema.md
    ├── postman/orders_api.postman_collection.json
    └── app/
        ├── main.py
        ├── config.py
        ├── database.py
        ├── models.py                 # Cart, CartItem, Order, OrderItem
        ├── schemas.py
        ├── catalog_client.py         # httpx-обёртка над catalog-service
        └── routers/
            ├── carts.py
            └── orders.py
```

## Быстрый старт

Требуется Docker Desktop / Docker Engine + Compose v2.

```bash
cd homework2-microservices
docker compose up --build
```

После запуска:

- catalog-service: <http://localhost:8001/docs> (Swagger UI), <http://localhost:8001/health>
- orders-service:  <http://localhost:8002/docs> (Swagger UI), <http://localhost:8002/health>
- catalog-db: `localhost:5433`, login `catalog/catalog`, db `catalog_db`
- orders-db:  `localhost:5434`, login `orders/orders`, db `orders_db`

При первом старте catalog-service автоматически создаст таблицы и засеет
**4 категории + 20 товаров**. Чтобы отключить сидинг — поставить
`SEED_ON_STARTUP=false` в окружении сервиса.

Остановка:

```bash
docker compose down            # сохранит данные в томах
docker compose down -v         # удалит и тома (полная очистка)
```

## API

### catalog-service (8001)

| Метод  | Путь                                | Назначение                        |
| ------ | ----------------------------------- | --------------------------------- |
| GET    | `/api/categories`                   | список категорий                  |
| POST   | `/api/categories`                   | создать категорию                 |
| PUT    | `/api/categories/{id}`              | обновить категорию                |
| DELETE | `/api/categories/{id}`              | удалить категорию                 |
| GET    | `/api/products`                     | список товаров (фильтры/сорт./пагинация) |
| GET    | `/api/products/{id}`                | карточка товара                   |
| POST   | `/api/products`                     | создать товар                     |
| PUT    | `/api/products/{id}`                | обновить товар                    |
| DELETE | `/api/products/{id}`                | удалить товар                     |
| PATCH  | `/api/products/{id}/stock`          | изменить остаток (`{"delta": N}`) |

Список товаров: `?category=1&socket_type=E27&power_watt=9&sort=price&order=asc&limit=20&offset=0`.

### orders-service (8002)

| Метод  | Путь                                       | Назначение                                  |
| ------ | ------------------------------------------ | ------------------------------------------- |
| POST   | `/api/cart`                                | создать корзину                             |
| GET    | `/api/cart/{session_id}`                   | получить корзину                            |
| DELETE | `/api/cart/{session_id}`                   | удалить корзину                             |
| POST   | `/api/cart/{session_id}/items`             | добавить позицию (с проверкой stock)        |
| PATCH  | `/api/cart/{session_id}/items/{item_id}`   | изменить количество                         |
| DELETE | `/api/cart/{session_id}/items/{item_id}`   | удалить позицию                             |
| POST   | `/api/orders`                              | оформить заказ из корзины (списывает stock) |
| GET    | `/api/orders`                              | список заказов (фильтр `?status=…`)         |
| GET    | `/api/orders/{order_number}`               | получить заказ по номеру                    |
| PATCH  | `/api/orders/{order_id}/status`            | сменить статус (с проверкой переходов)      |

### Бизнес-логика заказов

Статусы: `new → confirmed → shipped → delivered`. В любой момент до `shipped`
допустим переход в `cancelled`. При оформлении заказа orders-service вызывает
`PATCH /api/products/{id}/stock` в catalog-service с `delta=-quantity` для
каждой позиции. При отмене — возвращает остатки тем же эндпоинтом с
положительным `delta`.

## Postman

Коллекции лежат рядом с каждым сервисом:

- [`catalog-service/postman/catalog_api.postman_collection.json`](catalog-service/postman/catalog_api.postman_collection.json)
- [`orders-service/postman/orders_api.postman_collection.json`](orders-service/postman/orders_api.postman_collection.json)

В каждой коллекции есть переменная `{{base_url}}` (по умолчанию
`http://localhost:8001` и `http://localhost:8002`), а в orders ещё `{{session_id}}`,
`{{order_number}}` и `{{order_id}}` — удобно подменять под конкретный прогон.

### Сценарий ручной проверки (в Postman или curl)

1. `GET /health` обоих сервисов.
2. `GET /api/categories`, `GET /api/products?limit=5` → видим засеянные данные.
3. `POST /api/cart` `{"session_id":"demo-1"}` → корзина создана.
4. `POST /api/cart/demo-1/items` `{"product_id":1,"quantity":2}` → позиция добавлена,
   stock не уменьшился (резервация только на оформлении).
5. `POST /api/orders` `{"session_id":"demo-1", customer_*..., delivery_address:"..."}`
   → создан заказ, stock товара 1 уменьшился на 2, корзина удалена.
6. `GET /api/products/1` (на catalog) → убеждаемся, что `stock` уменьшился.
7. `PATCH /api/orders/{id}/status` `{"status":"confirmed"}` → статус сменился.
8. `PATCH /api/orders/{id}/status` `{"status":"cancelled"}` → переход `confirmed→cancelled`,
   stock товара 1 возвращён обратно.

## Локальный запуск без Docker (опционально)

Понадобятся Python 3.12 и две запущенные базы PostgreSQL.

```bash
# каталог
cd catalog-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg2://catalog:catalog@localhost:5432/catalog_db \
  uvicorn app.main:app --port 8001

# заказы (в другом терминале)
cd orders-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg2://orders:orders@localhost:5432/orders_db \
CATALOG_SERVICE_URL=http://localhost:8001 \
  uvicorn app.main:app --port 8002
```

## Соответствие критериям ТЗ ДЗ-2

| Критерий                            | Где                                                                |
| ----------------------------------- | ------------------------------------------------------------------ |
| Реализация микросервиса товаров     | `catalog-service/` — все эндпоинты ТЗ + категории + stock          |
| Реализация микросервиса заказов     | `orders-service/` — корзина, оформление, статусы, отмена           |
| Соответствие ТЗ                     | Совпадают таблицы/поля/эндпоинты разделов 4–6 ТЗ                   |
| Работа с БД (CRUD, сохранение)      | Postgres × 2, SQLAlchemy ORM, тома Docker, миграции `create_all`   |
