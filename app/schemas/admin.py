# app/schemas/admin.py
from pydantic import BaseModel, Field
from typing import Optional
from app.models import PanelType, NodeStatus

# ---- فرم افزودن سرور جدید ----
class NodeCreate(BaseModel):
    display_name: str = Field(..., description="نام نمایشی مثلا: سرور VIP آلمان")
    panel_type: PanelType
    api_url: str = Field(..., description="آدرس پنل مثل https://1.2.3.4:8000")
    api_token: str = Field(..., description="توکن ادمین پنل مقصد")
    status: NodeStatus = NodeStatus.ACTIVE
    is_visible_in_sub: bool = True

# ---- فرم ساخت نماینده جدید ----
class ResellerCreate(BaseModel):
    username: str
    password: str
    daily_subscription_fee: int = 0
    base_price_per_gb: int = 1000
    base_price_master_sub: int = 2000
    can_create_sub: bool = False

# ---- فرم تخصیص سرور به نماینده (تعیین قیمت) ----
class NodeAllocationCreate(BaseModel):
    node_id: int
    custom_price_per_gb: Optional[int] = None
    custom_price_per_day: Optional[int] = None
