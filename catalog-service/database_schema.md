# Catalog Service — схема БД

База: `catalog_db` (PostgreSQL 16). Создаётся автоматически при первом запуске
(`Base.metadata.create_all`) и заполняется демо-данными (4 категории + 20 ламп)
через `seed.py`, если установлена переменная `SEED_ON_STARTUP=true`.

## Таблица `categories`

| Поле | Тип             | Ограничения       | Описание                       |
| ---- | --------------- | ----------------- | ------------------------------ |
| id   | SERIAL          | PK                |                                |
| name | VARCHAR(100)    | NOT NULL          | Название, например «Светодиодные» |
| slug | VARCHAR(100)    | UNIQUE NOT NULL   | URL-slug, например `led`       |

## Таблица `products`

| Поле        | Тип            | Ограничения                              | Описание           |
| ----------- | -------------- | ---------------------------------------- | ------------------ |
| id          | SERIAL         | PK                                       |                    |
| category_id | INT            | FK → categories.id, NOT NULL             |                    |
| name        | VARCHAR(200)   | NOT NULL                                 |                    |
| sku         | VARCHAR(50)    | UNIQUE NOT NULL                          | Артикул            |
| description | TEXT           |                                          |                    |
| price       | NUMERIC(10,2)  | NOT NULL                                 |                    |
| stock       | INT            | NOT NULL DEFAULT 0                       | Остаток на складе  |
| power_watt  | INT            |                                          | Мощность, Вт       |
| socket_type | VARCHAR(20)    |                                          | E14, E27, GU10 …   |
| image_url   | VARCHAR(500)   |                                          |                    |
| created_at  | TIMESTAMPTZ    | NOT NULL DEFAULT now()                   |                    |
| updated_at  | TIMESTAMPTZ    | NOT NULL DEFAULT now() ON UPDATE now()   |                    |

## Эндпоинты

| Метод  | Путь                                   | Описание                       |
| ------ | -------------------------------------- | ------------------------------ |
| GET    | `/api/categories`                      | Список категорий               |
| POST   | `/api/categories`                      | Создать категорию              |
| PUT    | `/api/categories/{id}`                 | Обновить категорию             |
| DELETE | `/api/categories/{id}`                 | Удалить категорию              |
| GET    | `/api/products`                        | Список товаров (фильтры/сорт.) |
| GET    | `/api/products/{id}`                   | Карточка товара                |
| POST   | `/api/products`                        | Создать товар                  |
| PUT    | `/api/products/{id}`                   | Обновить товар                 |
| DELETE | `/api/products/{id}`                   | Удалить товар                  |
| PATCH  | `/api/products/{id}/stock`             | Изменить остаток (`delta`)     |

Параметры списка товаров: `category`, `socket_type`, `power_watt`, `sort` (id|name|price|stock|created_at), `order` (asc|desc), `limit`, `offset`.
