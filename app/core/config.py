# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Guardino Core API"
    VERSION: str = "1.0.0"
    
    # متغیر جدید برای دامنه داینامیک (در داکر از فایل .env خوانده می‌شود)
    # اگر در .env نباشد، از آدرس لوکال استفاده می‌کند
    SYSTEM_DOMAIN: str = "http://localhost:8000" 
    
    POSTGRES_USER: str = "guardino_admin"
    POSTGRES_PASSWORD: str = "super_secret_password_here"
    POSTGRES_DB: str = "guardino_core_db"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"
    
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_REPLACE_LATER_IN_PRODUCTION"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"

settings = Settings()
