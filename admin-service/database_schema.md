# admin-service — схема БД

База `admin_db` (PostgreSQL). Хранит только учётные записи менеджеров —
данные о товарах и заказах живут в своих микросервисах, admin обращается к ним
по HTTP.

## Таблица `admin_users`

| Поле            | Тип            | Ограничения              | Описание                          |
| --------------- | -------------- | ------------------------ | --------------------------------- |
| `id`            | integer        | PK, autoincrement        | идентификатор                     |
| `username`      | varchar(100)   | NOT NULL, UNIQUE         | логин менеджера                   |
| `password_hash` | varchar(255)   | NOT NULL                 | bcrypt-хеш пароля                 |
| `full_name`     | varchar(200)   | NULL                     | имя менеджера                     |
| `created_at`    | timestamp      | NOT NULL, default now()  | дата создания                     |

При первом старте (если таблица пуста и `SEED_ADMIN_ON_STARTUP=true`) создаётся
менеджер из `DEFAULT_ADMIN_USERNAME` / `DEFAULT_ADMIN_PASSWORD`
(по умолчанию `admin` / `admin123`).

## Аутентификация

`POST /api/auth/login` (form-data `username`, `password`) проверяет пароль через
bcrypt и выдаёт **JWT** (HS256, секрет `JWT_SECRET`, срок жизни
`ACCESS_TOKEN_TTL_MINUTES`). Токен передаётся в заголовке
`Authorization: Bearer <token>` ко всем `/api/admin/*` эндпоинтам.
