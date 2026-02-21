# app/services/marzban_adapter.py
import httpx
from typing import Optional, Dict, Any
from app.models import Node

class MarzbanAdapter:
    def __init__(self, node: Node):
        """
        این کلاس با دریافت اطلاعات یک نود از دیتابیس، به API مرزبان متصل می‌شود.
        """
        # پاکسازی آدرس از اسلش‌های اضافی
        self.base_url = node.api_url.rstrip("/") + "/api"
        
        # اگر در دیتابیس توکن ذخیره شده بود از آن استفاده می‌کنیم
        self.api_token = node.api_token
        self.headers = {"Accept": "application/json"}
        if self.api_token:
            self.headers["Authorization"] = f"Bearer {self.api_token}"

    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        تابع داخلی برای ارسال درخواست‌های HTTP (Async)
        """
        url = f"{self.base_url}{endpoint}"
        
        # استفاده از httpx برای درخواست‌های غیرهمگام (Async)
        # غیرفعال کردن verify=False برای جلوگیری از ارور SSL سرورهای نامعتبر
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data
            )
            
            # اگر خطایی رخ داد، اکسپشن تولید می‌کنیم تا لایه بالاتر آن را مدیریت (Rollback) کند
            response.raise_for_status()
            
            # اگر پاسخ JSON بود آن را برمی‌گردانیم، در غیر این صورت فقط متن را برمی‌گردانیم
            try:
                return response.json()
            except ValueError:
                return {"detail": response.text}

    async def get_token(self, username: str, password: str) -> str:
        """
        دریافت توکن ادمین از مرزبان
        """
        url = f"{self.base_url}/admin/token"
        data = {"grant_type": "password", "username": username, "password": password}
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            token_data = response.json()
            self.api_token = token_data.get("access_token")
            self.headers["Authorization"] = f"Bearer {self.api_token}"
            return self.api_token

    async def create_user(self, username: str, expire: int, data_limit: int, proxies: Dict, inbounds: Dict) -> Dict:
        """
        ساخت کاربر جدید در مرزبان
        """
        payload = {
            "username": username,
            "proxies": proxies,
            "inbounds": inbounds,
            "expire": expire,
            "data_limit": data_limit
        }
        return await self._make_request("POST", "/user", data=payload)

    async def get_user(self, username: str) -> Dict:
        """
        دریافت اطلاعات و میزان مصرف یک کاربر
        """
        return await self._make_request("GET", f"/user/{username}")

    async def modify_user(self, username: str, data_limit: int, expire: int) -> Dict:
        """
        ویرایش حجم و زمان کاربر
        """
        payload = {"data_limit": data_limit, "expire": expire}
        return await self._make_request("PUT", f"/user/{username}", data=payload)

    async def delete_user(self, username: str) -> Dict:
        """
        حذف کامل کاربر از مرزبان
        """
        return await self._make_request("DELETE", f"/user/{username}")

    async def suspend_user(self, username: str) -> Dict:
        """
        مسدود کردن کاربر (بدون پاک کردن آن)
        نکته: مرزبان در آپدیت‌های جدید فیلد status را در بدنه PUT می‌پذیرد
        """
        payload = {"status": "disabled"}
        return await self._make_request("PUT", f"/user/{username}", data=payload)

    async def get_subscription_link(self, username: str) -> str:
        """
        دریافت لینک ساب خامِ مرزبان برای این کاربر
        """
        user_data = await self.get_user(username)
        # تلاش برای پیدا کردن فیلد لینک ساب بر اساس نسخه‌های مختلف API مرزبان
        sub_url = user_data.get("subscription_url")
        if not sub_url and "links" in user_data and len(user_data["links"]) > 0:
            sub_url = user_data["links"][0]
            
        return sub_url
