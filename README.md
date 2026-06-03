# Интернет-магазин лампочек — итоговый проект (микросервисы)

Полностью рабочий интернет-магазин на микросервисной архитектуре.

- **Пользователь** просматривает товары, добавляет их в корзину и оформляет заказ
  (витрина `storefront`).
- **Менеджер** заходит в панель управления по логину и паролю, управляет товарами
  (просмотр, добавление, изменение, удаление) и заказами (просмотр и смена статусов).

## Состав проекта

Три микросервиса + витрина для покупателя:

| Компонент           | Порт   | Назначение                                                            |
| ------------------- | ------ | --------------------------------------------------------------------- |
| **catalog-service** | `8001` | Микросервис **управления товарами**: товары, категории, остатки.      |
| **orders-service**  | `8002` | Микросервис **управления заказами**: корзины, оформление, статусы.    |
| **admin-service**   | `8003` | Микросервис **панели управления**: авторизация менеджера + UI.        |
| **storefront**      | `8090` | Витрина покупателя (статика на nginx): каталог, корзина, оформление.  |

Каждый микросервис — отдельное приложение со **своей базой данных** (PostgreSQL),
сервисы общаются по HTTP.

```
              ┌──────────────┐         ┌──────────────┐
  покупатель  │  storefront  │  ─────► │   catalog    │ ◄───┐
   (браузер)  │   (nginx)    │  ─────► │   (8001)     │     │ HTTP
              └──────────────┘    ┌──► │   catalog-db │     │
                     │            │    └──────────────┘     │
                     └────────────┤                         │
                                  └──► ┌──────────────┐     │
                                       │   orders     │ ────┘
                                       │   (8002)     │
              ┌──────────────┐         │   orders-db  │
   менеджер   │ admin-service│  ─────► └──────────────┘
   (браузер)  │  (8003) + UI │  ─────► (catalog + orders как BFF-шлюз)
              │   admin-db   │
              └──────────────┘
```

`admin-service` выступает **аутентифицированным шлюзом (BFF)**: панель управления
ходит только в него, а он — с проверкой JWT — проксирует запросы в `catalog` и
`orders`. Так управление товарами/заказами защищено логином и паролем.

## Стек

- Python 3.12 + **FastAPI**
- **SQLAlchemy 2** + **psycopg2** + **PostgreSQL 16** (× 3 БД)
- Pydantic v2 + `pydantic-settings`
- `httpx` — межсервисные вызовы
- **JWT** (PyJWT) + **bcrypt** (passlib) — авторизация менеджера
- **nginx** + ванильный JS — витрина и панель управления (без фронтенд-сборки)
- **Docker Compose** — оркестрация (3 БД + 3 сервиса + витрина)

## Структура

```
WebDev_HW2/
├── docker-compose.yml
├── README.md
├── catalog-service/         # микросервис товаров (FastAPI + Postgres)
│   ├── app/ …               # main, models, schemas, routers/{products,categories}
│   ├── seed.py              # 4 категории + 20 ламп
│   └── postman/
├── orders-service/          # микросервис заказов (FastAPI + Postgres)
│   ├── app/ …               # main, models, schemas, catalog_client, routers/{carts,orders}
│   └── postman/
├── admin-service/           # микросервис панели управления (FastAPI + Postgres)
│   ├── app/
│   │   ├── main.py          # FastAPI, сидинг менеджера, отдача статики
│   │   ├── security.py      # bcrypt + JWT
│   │   ├── deps.py          # проверка токена (get_current_user)
│   │   ├── clients.py       # httpx-шлюз к catalog и orders
│   │   ├── models.py        # AdminUser
│   │   └── routers/{auth,products,orders}.py
│   ├── static/              # UI панели: index.html, app.js, styles.css
│   └── postman/
└── storefront/              # витрина покупателя (nginx + статика)
    ├── Dockerfile
    ├── nginx.conf
    └── public/              # index.html, app.js, styles.css, config.js
```

## Быстрый старт

Требуется Docker Desktop / Docker Engine + Compose v2.

```bash
docker compose up --build
```

После запуска открыть в браузере:

- 🛍️ **Витрина покупателя** — <http://localhost:8090>
- 🔧 **Панель управления** — <http://localhost:8003>
  (логин по умолчанию **`admin`** / пароль **`admin123`**)

Swagger-документация API каждого сервиса:

- catalog: <http://localhost:8001/docs>
- orders:  <http://localhost:8002/docs>
- admin:   <http://localhost:8003/docs>

При первом старте `catalog-service` создаёт таблицы и засеивает
**4 категории + 20 товаров**, а `admin-service` создаёт менеджера по умолчанию.

Остановка:

```bash
docker compose down       # сохранит данные в томах
docker compose down -v    # удалит и тома (полная очистка)
```

> Порты можно поменять в `docker-compose.yml`. Витрина обращается к catalog/orders
> по адресам из `storefront/public/config.js` — при смене портов поправьте его.

## Пользовательский сценарий (витрина, 8090)

1. Открыть <http://localhost:8090> — загружается каталог товаров из `catalog-service`.
2. Фильтровать по категории, нажать **«В корзину»** на нужных товарах.
3. Открыть корзину (кнопка 🛒): менять количество, удалять позиции — всё через
   `orders-service`.
4. Нажать **«Оформить заказ»**, заполнить имя/телефон/email/адрес, подтвердить.
   `orders-service` создаёт заказ, списывает остатки в `catalog-service` и очищает
   корзину. Покупатель видит номер заказа `ORD-…`.

## Сценарий менеджера (панель, 8003)

1. Открыть <http://localhost:8003>, войти как `admin / admin123` → получаем JWT.
2. Вкладка **«Товары»**: список, **добавить** / **изменить** / **удалить** товар
   (запросы идут в `catalog-service` через шлюз с проверкой токена).
3. Вкладка **«Заказы»**: список заказов с фильтром по статусу, **смена статуса**
   заказа (`new → confirmed → shipped → delivered`, отмена `→ cancelled`).

## API

### catalog-service (8001) — товары

| Метод  | Путь                          | Назначение                               |
| ------ | ----------------------------- | ---------------------------------------- |
| GET    | `/api/categories`             | список категорий                         |
| POST   | `/api/categories`             | создать категорию                        |
| PUT    | `/api/categories/{id}`        | обновить категорию                       |
| DELETE | `/api/categories/{id}`        | удалить категорию                        |
| GET    | `/api/products`               | список товаров (фильтры/сорт./пагинация) |
| GET    | `/api/products/{id}`          | карточка товара                          |
| POST   | `/api/products`               | создать товар                            |
| PUT    | `/api/products/{id}`          | обновить товар                           |
| DELETE | `/api/products/{id}`          | удалить товар                            |
| PATCH  | `/api/products/{id}/stock`    | изменить остаток (`{"delta": N}`)        |

### orders-service (8002) — корзины и заказы

| Метод  | Путь                                     | Назначение                          |
| ------ | ---------------------------------------- | ----------------------------------- |
| POST   | `/api/cart`                              | создать корзину                     |
| GET    | `/api/cart/{session_id}`                 | получить корзину                    |
| DELETE | `/api/cart/{session_id}`                 | удалить корзину                     |
| POST   | `/api/cart/{session_id}/items`           | добавить позицию (проверка stock)   |
| PATCH  | `/api/cart/{session_id}/items/{item_id}` | изменить количество                 |
| DELETE | `/api/cart/{session_id}/items/{item_id}` | удалить позицию                     |
| POST   | `/api/orders`                            | оформить заказ (списывает stock)    |
| GET    | `/api/orders`                            | список заказов (фильтр `?status=…`) |
| GET    | `/api/orders/{order_number}`             | заказ по номеру                     |
| PATCH  | `/api/orders/{order_id}/status`          | сменить статус (проверка переходов) |

### admin-service (8003) — панель управления

| Метод  | Путь                                  | Назначение                                  |
| ------ | ------------------------------------- | ------------------------------------------- |
| POST   | `/api/auth/login`                     | вход менеджера (form `username`+`password`) → JWT |
| GET    | `/api/auth/me`                        | текущий менеджер (по токену)                |
| GET    | `/api/admin/categories`               | категории (для форм) 🔒                     |
| POST   | `/api/admin/categories`               | создать категорию 🔒                        |
| GET    | `/api/admin/products`                 | список товаров 🔒                           |
| GET    | `/api/admin/products/{id}`            | товар 🔒                                    |
| POST   | `/api/admin/products`                 | создать товар 🔒                            |
| PUT    | `/api/admin/products/{id}`            | изменить товар 🔒                           |
| DELETE | `/api/admin/products/{id}`            | удалить товар 🔒                            |
| GET    | `/api/admin/orders`                   | список заказов (фильтр `?status=…`) 🔒      |
| GET    | `/api/admin/orders/{order_number}`    | заказ по номеру 🔒                          |
| PATCH  | `/api/admin/orders/{order_id}/status` | сменить статус заказа 🔒                    |

🔒 — требуется заголовок `Authorization: Bearer <token>`.

### Бизнес-логика заказов

Статусы: `new → confirmed → shipped → delivered`. В любой момент до `shipped`
допустим переход в `cancelled`. При оформлении заказа `orders-service` вызывает
`PATCH /api/products/{id}/stock` в `catalog-service` (списание остатков), при
отмене — возвращает остатки положительным `delta`. Недопустимые переходы статусов
отклоняются (HTTP 409).

## Postman

Коллекции лежат рядом с каждым сервисом:

- [`catalog-service/postman/catalog_api.postman_collection.json`](catalog-service/postman/catalog_api.postman_collection.json)
- [`orders-service/postman/orders_api.postman_collection.json`](orders-service/postman/orders_api.postman_collection.json)
- [`admin-service/postman/admin_api.postman_collection.json`](admin-service/postman/admin_api.postman_collection.json)

В коллекции admin запрос **Auth: login** автоматически сохраняет JWT в переменную
`{{token}}`, которую используют остальные запросы.

## Переменные окружения (основные)

| Сервис  | Переменная               | По умолчанию                  | Назначение                       |
| ------- | ------------------------ | ----------------------------- | -------------------------------- |
| catalog | `SEED_ON_STARTUP`        | `true`                        | сидинг товаров при старте        |
| orders  | `CATALOG_SERVICE_URL`    | `http://catalog-service:8001` | адрес каталога                   |
| admin   | `JWT_SECRET`             | `dev-secret-change-me`        | секрет подписи токенов           |
| admin   | `DEFAULT_ADMIN_USERNAME` | `admin`                       | логин менеджера по умолчанию     |
| admin   | `DEFAULT_ADMIN_PASSWORD` | `admin123`                    | пароль менеджера по умолчанию    |

## Локальный запуск без Docker (опционально)

Понадобятся Python 3.12 и запущенные базы PostgreSQL. Пример для admin-service:

```bash
cd admin-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg2://admin:admin@localhost:5432/admin_db \
CATALOG_SERVICE_URL=http://localhost:8001 \
ORDERS_SERVICE_URL=http://localhost:8002 \
  uvicorn app.main:app --port 8003
```

catalog-service и orders-service запускаются аналогично (см. их `requirements.txt`).
