# app/services/wgdashboard_adapter.py
import httpx
from typing import Optional, Dict, Any
from app.models import Node

class WGDashboardAdapter:
    def __init__(self, node: Node):
        """
        اتصال به پنل WGDashboard
        """
        self.base_url = node.api_url.rstrip("/")
        # در WGDashboard توکن معمولاً در هدر Authorization ارسال می‌شود
        self.api_token = node.api_token
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_token}"
        }

    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.request(method=method, url=url, headers=self.headers, json=data)
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                return {"detail": response.text}

    async def create_user(self, username: str) -> Dict:
        """
        ساخت Peer جدید در وایرگارد. 
        نکته: وایرگارد محدودیت حجم و زمان ذاتی ندارد، گاردینو باید خودش آن را کنترل کند.
        """
        payload = {
            "name": username,
            # پارامترهای پیش‌فرض وایرگارد برای IP داینامیک
            "allocate_ips": True 
        }
        # مسیر فرضی بر اساس استانداردهای WG Dashboard
        return await self._make_request("POST", "/api/wireguard/client", data=payload)

    async def get_user(self, username: str) -> Dict:
        return await self._make_request("GET", f"/api/wireguard/client/{username}")

    async def delete_user(self, username: str) -> Dict:
        """حذف Peer از وایرگارد"""
        return await self._make_request("DELETE", f"/api/wireguard/client/{username}")

    async def suspend_user(self, username: str) -> Dict:
        """غیرفعال کردن (Disable) کانفیگ در وایرگارد"""
        payload = {"enabled": False}
        return await self._make_request("PUT", f"/api/wireguard/client/{username}/status", data=payload)

    async def get_subscription_link(self, username: str) -> str:
        """
        وایرگارد لینک ساب ندارد، بلکه فایل conf. برمی‌گرداند.
        ما آدرس دانلود مستقیم کانفیگ را تولید می‌کنیم تا گاردینو آن را ترکیب کند.
        """
        return f"{self.base_url}/api/wireguard/client/{username}/configuration"
