# app/services/marzban_adapter.py
import httpx
from typing import Optional, Dict, Any
from app.models import Node

class MarzbanAdapter:
    def __init__(self, node: Node):
        self.base_url = node.api_url.rstrip("/") + "/api"
        self.api_token = node.api_token
        self.headers = {"Accept": "application/json"}
        
        if self.api_token and ":" in self.api_token and len(self.api_token) < 100:
            self.username, self.password = self.api_token.split(":", 1)
            self.is_auto_auth = True
        else:
            self.is_auto_auth = False
            if self.api_token:
                self.headers["Authorization"] = f"Bearer {self.api_token}"

    async def get_token(self) -> str:
        url = f"{self.base_url}/admin/token"
        data = {"grant_type": "password", "username": self.username, "password": self.password}
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, data=data)
            response.raise_for_status() # اگر رمز غلط باشد اینجا ارور می‌دهد
            token_data = response.json()
            self.api_token = token_data.get("access_token")
            self.headers["Authorization"] = f"Bearer {self.api_token}"
            return self.api_token

    async def test_connection(self) -> bool:
        """تست زنده اتصال به سرور (جدید)"""
        try:
            if self.is_auto_auth:
                await self.get_token()
                return True
            else:
                # تست با توکن ثابت
                url = f"{self.base_url}/admin"
                async with httpx.AsyncClient(verify=False) as client:
                    res = await client.get(url, headers=self.headers)
                    res.raise_for_status()
                    return True
        except Exception as e:
            raise ValueError(f"ارتباط با سرور مرزبان شکست خورد. یوزر/پسورد یا آدرس را بررسی کنید.")

    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        if self.is_auto_auth and "Authorization" not in self.headers:
            await self.get_token()

        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.request(method=method, url=url, headers=self.headers, json=data)
            if response.status_code == 401 and self.is_auto_auth:
                await self.get_token()
                response = await client.request(method=method, url=url, headers=self.headers, json=data)
                
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                return {"detail": response.text}

    async def get_inbounds(self) -> Dict:
        return await self._make_request("GET", "/inbounds")

    async def create_user(self, username: str, expire: int, data_limit: int, proxies: Dict = None) -> Dict:
        if proxies is None or not proxies:
            proxies = {"vless": {}, "vmess": {}, "trojan": {}}

        inbounds_data = await self.get_inbounds()
        inbounds = {}
        if isinstance(inbounds_data, dict) and "detail" not in inbounds_data:
            for proto, list_inbounds in inbounds_data.items():
                if proto in proxies:
                    inbounds[proto] = [ib["tag"] for ib in list_inbounds]
        
        payload = {"username": username, "proxies": proxies, "inbounds": inbounds, "expire": expire, "data_limit": data_limit}
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
