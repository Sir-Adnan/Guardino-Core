# app/api/subscriptions.py
import base64
import httpx
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import GuardinoUser, SubAccount
from app.services.node_factory import NodeFactory

router = APIRouter(tags=["Subscriptions"])

@router.get("/sub/{token}", response_class=PlainTextResponse)
async def get_master_subscription(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    دریافت لینک ساب مستر.
    این API خروجی متنی (Plain Text) دارد که معمولاً Base64 است و کلاینت‌های VPN آن را می‌فهمند.
    """
    
    # 1. جستجوی کاربر در دیتابیس با استفاده از توکن یکتا
    # ما با selectinload به دیتابیس می‌گوییم که اطلاعات نودهای این کاربر را هم همزمان بیاور (برای سرعت بیشتر)
    query = await db.execute(
        select(GuardinoUser)
        .options(selectinload(GuardinoUser.sub_accounts).selectinload(SubAccount.node))
        .where(GuardinoUser.sub_token == token)
    )
    user = query.scalar_one_or_none()

    # اگر کاربر نبود
    if not user:
        raise HTTPException(status_code=404, detail="لینک اشتراک معتبر نیست.")

    # 2. اگر کاربر غیرفعال یا منقضی شده بود، یک لیست خالی یا پیام خطا در ساب برمی‌گردانیم
    if user.status != "active":
        # ارسال یک کانفیگ فیک برای اطلاع‌رسانی به کاربر که اکانتش مسدود است
        msg = "vless://00000000-0000-0000-0000-000000000000@127.0.0.1:80?security=none&type=tcp#❌_Account_Suspended_or_Expired"
        return base64.b64encode(msg.encode("utf-8")).decode("utf-8")

    # 3. تابع کمکی برای دریافت و رمزگشایی سابِ هر پنل
    async def fetch_and_decode(sub_acc: SubAccount):
        node = sub_acc.node
        
        # منطق طلایی: اگر ادمین نود را آفلاین کرده یا تیک "نمایش در ساب" را برداشته، هیچ‌چیز برنگردان
        if node.status != "active" or not node.is_visible_in_sub:
            return ""
            
        try:
            adapter = NodeFactory.get_adapter(node)
            # گرفتن آدرس ساب بومی از مرزبان/پاسارگاد
            sub_url = await adapter.get_subscription_link(sub_acc.remote_identifier)
            if not sub_url:
                return ""
            
            # اتصال به سرور اصلی برای خواندن محتوای فایل ساب
            async with httpx.AsyncClient(verify=False) as client:
                # User-Agent کلاینت را به سرور اصلی پاس می‌دهیم تا اگر خروجی کلش یا xray متفاوت بود، درست عمل کند
                headers = {"User-Agent": request.headers.get("User-Agent", "v2rayNG")}
                resp = await client.get(sub_url, headers=headers, timeout=10.0)
                resp.raise_for_status()
                
                b64_content = resp.text.strip()
                
                # رمزگشایی Base64 به متن خام (vless://...)
                padding = len(b64_content) % 4
                if padding:
                    b64_content += '=' * (4 - padding)
                raw_text = base64.b64decode(b64_content).decode("utf-8")
                
                return raw_text
                
        except Exception as e:
            # اگر یک سرور تایم‌اوت داد، کل ساب خراب نمی‌شود، فقط کانفیگ آن سرور را رد می‌کنیم
            print(f"Error fetching from Node {node.display_name}: {e}")
            return ""

    # 4. اجرای موازی (درخواست همزمان به تمام سرورهایی که این کاربر در آن‌ها اکانت دارد)
    fetch_tasks = [fetch_and_decode(acc) for acc in user.sub_accounts]
    results = await asyncio.gather(*fetch_tasks)
    
    # 5. ترکیب (Merge) تمام کانفیگ‌های خام
    combined_raw_text = "\n".join([r.strip() for r in results if r.strip()])
    
    if not combined_raw_text:
        # اگر همه سرورها قطع بودند
        msg = "vless://00000000-0000-0000-0000-000000000000@127.0.0.1:80?security=none&type=tcp#⚠️_No_Active_Nodes_Available"
        return base64.b64encode(msg.encode("utf-8")).decode("utf-8")

    # 6. رمزنگاری مجدد به Base64 برای ارائه به کلاینت کاربر نهایی
    final_b64 = base64.b64encode(combined_raw_text.encode("utf-8")).decode("utf-8")
    
    return final_b64
