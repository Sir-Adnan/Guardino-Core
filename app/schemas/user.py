# app/schemas/user.py
from pydantic import BaseModel, Field
from typing import List

class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="نام کاربری مشتری")
    data_limit_gb: float = Field(..., ge=0, description="حجم کل به گیگابایت (0 برای نامحدود)")
    expire_days: int = Field(..., ge=0, description="تعداد روز اعتبار (0 برای نامحدود)")
    node_ids: List[int] = Field(..., min_items=1, description="لیست آیدی سرورهایی که کاربر باید روی آن‌ها ساخته شود")
    
    # تنظیمات پیش‌فرض برای پاسارگاد و مرزبان (اگر نماینده پروتکل خاصی خواست)
    # در نسخه پیشرفته، این‌ها را می‌توان از دیتابیس خواند
    proxies: dict = Field(default={"vless": {}}, description="تنظیمات پروتکل مرزبان")
    proxy_settings: dict = Field(default={"vless": {}}, description="تنظیمات پروتکل پاسارگاد")

class UserCreateResponse(BaseModel):
    message: str
    username: str
    total_cost: int
    sub_link: str

    class Config:
        from_attributes = True
