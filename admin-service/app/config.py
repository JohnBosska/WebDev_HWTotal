from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://admin:admin@admin-db:5432/admin_db"
    catalog_service_url: str = "http://catalog-service:8001"
    orders_service_url: str = "http://orders-service:8002"
    upstream_request_timeout: float = 5.0

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 720  # 12 часов

    # Учётка менеджера по умолчанию (создаётся при старте, если БД пуста)
    seed_admin_on_startup: bool = True
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
