# Orders Service — схема БД

База: `orders_db` (PostgreSQL 16). Таблицы создаются автоматически при первом
запуске (`Base.metadata.create_all`).

## Таблица `carts`

| Поле       | Тип             | Ограничения            |
| ---------- | --------------- | ---------------------- |
| id         | SERIAL          | PK                     |
| session_id | VARCHAR(100)    | UNIQUE NOT NULL        |
| created_at | TIMESTAMPTZ     | NOT NULL DEFAULT now() |

## Таблица `cart_items`

| Поле           | Тип            | Ограничения                              |
| -------------- | -------------- | ---------------------------------------- |
| id             | SERIAL         | PK                                       |
| cart_id        | INT            | FK → carts.id ON DELETE CASCADE, NOT NULL|
| product_id     | INT            | NOT NULL (ссылка в catalog-service)      |
| quantity       | INT            | NOT NULL                                 |
| price_snapshot | NUMERIC(10,2)  | NOT NULL                                 |

## Таблица `orders`

| Поле             | Тип              | Ограничения                            |
| ---------------- | ---------------- | -------------------------------------- |
| id               | SERIAL           | PK                                     |
| order_number     | VARCHAR(20)      | UNIQUE NOT NULL                        |
| customer_name    | VARCHAR(200)     | NOT NULL                               |
| customer_phone   | VARCHAR(20)      | NOT NULL                               |
| customer_email   | VARCHAR(100)     | NOT NULL                               |
| delivery_address | TEXT             | NOT NULL                               |
| total_amount     | NUMERIC(10,2)    | NOT NULL                               |
| status           | ENUM order_status| NOT NULL DEFAULT 'new'                 |
| created_at       | TIMESTAMPTZ      | NOT NULL DEFAULT now()                 |
| updated_at       | TIMESTAMPTZ      | NOT NULL DEFAULT now() ON UPDATE now() |

`order_status`: `new`, `confirmed`, `shipped`, `delivered`, `cancelled`.

## Таблица `order_items`

| Поле         | Тип            | Ограничения                                |
| ------------ | -------------- | ------------------------------------------ |
| id           | SERIAL         | PK                                         |
| order_id     | INT            | FK → orders.id ON DELETE CASCADE, NOT NULL |
| product_id   | INT            | NOT NULL                                   |
| product_name | VARCHAR(200)   | NOT NULL                                   |
| quantity     | INT            | NOT NULL                                   |
| price        | NUMERIC(10,2)  | NOT NULL                                   |

## Эндпоинты

| Метод  | Путь                                      | Описание                                   |
| ------ | ----------------------------------------- | ------------------------------------------ |
| POST   | `/api/cart`                               | Создать корзину                            |
| GET    | `/api/cart/{session_id}`                  | Получить корзину                           |
| DELETE | `/api/cart/{session_id}`                  | Удалить корзину                            |
| POST   | `/api/cart/{session_id}/items`            | Добавить позицию                           |
| PATCH  | `/api/cart/{session_id}/items/{item_id}`  | Изменить количество                        |
| DELETE | `/api/cart/{session_id}/items/{item_id}`  | Удалить позицию                            |
| POST   | `/api/orders`                             | Оформить заказ из корзины                  |
| GET    | `/api/orders`                             | Список заказов (фильтр по `status`)        |
| GET    | `/api/orders/{order_number}`              | Получить заказ по номеру                   |
| PATCH  | `/api/orders/{order_id}/status`           | Сменить статус (с проверкой переходов)     |

## Бизнес-правила

- Переходы статусов: `new → confirmed → shipped → delivered`. В любой момент до
  `shipped` допустим переход в `cancelled`.
- При **создании заказа** для каждой позиции вызывается
  `PATCH /api/products/{id}/stock` в catalog-service с `delta=-quantity`.
  Если хоть одна позиция не списывается — все ранее зарезервированные позиции
  возвращаются обратно (компенсация).
- При **отмене заказа** (`status=cancelled`) для каждой позиции вызывается
  `PATCH /api/products/{id}/stock` с `delta=+quantity`.
- В корзину можно добавлять только то, что есть на складе (проверка `stock`).
- `price_snapshot` фиксирует цену на момент добавления в корзину; для оформленного
  заказа цены копируются в `order_items.price`.
