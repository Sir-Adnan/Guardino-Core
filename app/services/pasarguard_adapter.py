# app/services/pasarguard_adapter.py
import httpx
from typing import Optional, Dict, Any
from app.models import Node

class PasarguardAdapter:
    def __init__(self, node: Node):
        """
        اتصال به هسته پاسارگاد بر اساس مدل نود در دیتابیس
        """
        self.base_url = node.api_url.rstrip("/")
        self.api_token = node.api_token
        self.headers = {"Accept": "application/json"}
        if self.api_token:
            self.headers["Authorization"] = f"Bearer {self.api_token}"

    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.request(method=method, url=url, headers=self.headers, json=data)
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                return {"detail": response.text}

    async def create_user(self, username: str, expire: int, data_limit: int, proxy_settings: Dict) -> Dict:
        """
        ساخت کاربر در پاسارگاد. 
        دقت کنید پاسارگاد از فیلد proxy_settings استفاده می‌کند.
        """
        payload = {
            "username": username,
            "proxy_settings": proxy_settings,
            "expire": expire,
            "data_limit": data_limit,
            "status": "active"
        }
        return await self._make_request("POST", "/api/user", data=payload)

    async def get_user(self, username: str) -> Dict:
        """دریافت اطلاعات کاربر از پاسارگاد"""
        return await self._make_request("GET", f"/api/user/{username}")

    async def modify_user(self, username: str, data_limit: int, expire: int) -> Dict:
        """ویرایش حجم و زمان"""
        payload = {"data_limit": data_limit, "expire": expire}
        return await self._make_request("PUT", f"/api/user/{username}", data=payload)

    async def delete_user(self, username: str) -> Dict:
        """حذف کاربر"""
        return await self._make_request("DELETE", f"/api/user/{username}")

    async def suspend_user(self, username: str) -> Dict:
        """مسدود کردن کاربر با تغییر وضعیت به disabled"""
        payload = {"status": "disabled"}
        return await self._make_request("PUT", f"/api/user/{username}", data=payload)

    async def get_subscription_link(self, username: str) -> str:
        """دریافت لینک ساب از پاسارگاد"""
        user_data = await self.get_user(username)
        # پاسارگاد لینک ساب را معمولاً در فیلد subscription_url برمی‌گرداند
        return user_data.get("subscription_url", "")
