# create_superadmin.py
import asyncio
from app.core.database import AsyncSessionLocal
from app.models import Reseller
from app.core.security import get_password_hash

async def init_superadmin():
    async with AsyncSessionLocal() as db:
        # نام کاربری و رمز عبور پیش‌فرض ادمین کل
        admin = Reseller(
            username="guardino_admin",
            password_hash=get_password_hash("Admin@12345"),
            balance=99999999999,  # ادمین کل نیازی به موجودی ندارد، اما برای جلوگیری از ارور، یک عدد نجومی می‌گذاریم
            parent_id=None,       # مهم‌ترین بخش: نال بودن یعنی این شخص ادمین کل است
            can_create_sub=True,  # اجازه زیرمجموعه‌گیری
            base_price_per_gb=0,
            base_price_master_sub=0
        )
        db.add(admin)
        await db.commit()
        print("✅ Super Admin 'guardino_admin' created successfully!")

if __name__ == "__main__":
    asyncio.run(init_superadmin())
