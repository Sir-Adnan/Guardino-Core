# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# ساخت موتور اتصال ناهمگام (Async Engine)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False, # در حالت توسعه می‌توانید True کنید تا کوئری‌ها را در کنسول ببینید
    future=True,
    pool_size=20,        # مدیریت کانکشن‌های همزمان
    max_overflow=10
)

# ساخت کارخانه تولید سشن (Session Factory)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# کلاس پایه برای تمام جداول دیتابیس
Base = declarative_base()

# تابع سازنده برای استفاده در APIها (Dependency Injection)
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
