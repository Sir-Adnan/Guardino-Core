# app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Guardino Core API"
    VERSION: str = "1.0.0"
    
    # تنظیمات دیتابیس PostgreSQL (از نوع Async برای سرعت بالا)
    POSTGRES_USER: str = "guardino_admin"
    POSTGRES_PASSWORD: str = "super_secret_password_here"
    POSTGRES_DB: str = "guardino_core_db"
    POSTGRES_HOST: str = "db" # در داکر، اسم سرویس db است
    POSTGRES_PORT: str = "5432"
    
    # کلید امنیتی برای ساخت توکن‌های API نمایندگان و لینک ساب
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_REPLACE_LATER_IN_PRODUCTION"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"

settings = Settings()
