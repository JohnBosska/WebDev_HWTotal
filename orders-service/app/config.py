from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://orders:orders@orders-db:5432/orders_db"
    catalog_service_url: str = "http://catalog-service:8001"
    catalog_request_timeout: float = 5.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
