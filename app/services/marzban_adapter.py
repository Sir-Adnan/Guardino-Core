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
        self.api_token = node.api_token
        self.headers = {"Accept": "application/json"}
        
        # سیستم هوشمند: تشخیص اینکه آیا کاربر username:password وارد کرده یا توکن مستقیم
        if self.api_token and ":" in self.api_token and len(self.api_token) < 100:
            self.username, self.password = self.api_token.split(":", 1)
            self.is_auto_auth = True
        else:
            self.is_auto_auth = False
            if self.api_token:
                self.headers["Authorization"] = f"Bearer {self.api_token}"

    async def get_token(self) -> str:
        """
        دریافت خودکار توکن ادمین از مرزبان
        """
        url = f"{self.base_url}/admin/token"
        data = {"grant_type": "password", "username": self.username, "password": self.password}
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            token_data = response.json()
            self.api_token = token_data.get("access_token")
            self.headers["Authorization"] = f"Bearer {self.api_token}"
            return self.api_token

    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        تابع داخلی برای ارسال درخواست‌های HTTP (Async)
        """
        # اگر لاگین هوشمند است و هنوز هدر Authorization نداریم، توکن بگیر
        if self.is_auto_auth and "Authorization" not in self.headers:
            await self.get_token()

        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data
            )
            
            # اگر توکن قبلی منقضی شده بود (ارور 401)، دوباره توکن جدید می‌گیریم و درخواست را تکرار می‌کنیم
            if response.status_code == 401 and self.is_auto_auth:
                await self.get_token()
                response = await client.request(
                    method=method, url=url, headers=self.headers, json=data
                )
                
            response.raise_for_status()
            
            try:
                return response.json()
            except ValueError:
                return {"detail": response.text}

    async def create_user(self, username: str, expire: int, data_limit: int, proxies: Dict, inbounds: Dict) -> Dict:
        payload = {
            "username": username,
            "proxies": proxies,
            "inbounds": inbounds,
            "expire": expire,
            "data_limit": data_limit
        }
        return await self._make_request("POST", "/user", data=payload)

    async def get_user(self, username: str) -> Dict:
        return await self._make_request("GET", f"/user/{username}")

    async def modify_user(self, username: str, data_limit: int, expire: int) -> Dict:
        payload = {"data_limit": data_limit, "expire": expire}
        return await self._make_request("PUT", f"/user/{username}", data=payload)

    async def delete_user(self, username: str) -> Dict:
        return await self._make_request("DELETE", f"/user/{username}")

    async def suspend_user(self, username: str) -> Dict:
        payload = {"status": "disabled"}
        return await self._make_request("PUT", f"/user/{username}", data=payload)

    async def get_subscription_link(self, username: str) -> str:
        user_data = await self.get_user(username)
        sub_url = user_data.get("subscription_url")
        if not sub_url and "links" in user_data and len(user_data["links"]) > 0:
            sub_url = user_data["links"][0]
            
        return sub_url
