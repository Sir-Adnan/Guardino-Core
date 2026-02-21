# app/models.py
import enum
from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, Boolean, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

# ================= ENUMS (وضعیت‌های ثابت سیستم) =================
class ResellerStatus(str, enum.Enum):
    ACTIVE = "active"
    LOCKED = "locked"       # فقط دسترسی خواندن (موجودی منفی)
    SUSPENDED = "suspended" # مسدود کامل

class PanelType(str, enum.Enum):
    MARZBAN = "marzban"
    PASARGUARD = "pasarguard"
    WGDASHBOARD = "wgdashboard"

class NodeStatus(str, enum.Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"

class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    EXPIRED = "expired"

class TransactionType(str, enum.Enum):
    BUY_VPN = "buy_vpn"
    REFUND = "refund"
    DAILY_FEE = "daily_fee"
    WALLET_CHARGE = "wallet_charge"

# ================= 1. جدول نمایندگان (شبکه هرمی) =================
class Reseller(Base):
    __tablename__ = "resellers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    balance: Mapped[int] = mapped_column(BigInteger, default=0)
    
    # تنظیمات مالی سیستم هرمی
    base_price_per_gb: Mapped[int] = mapped_column(Integer, default=1000) # قیمت پایه تک‌نود
    base_price_master_sub: Mapped[int] = mapped_column(Integer, default=2000) # قیمت پایه لینک ترکیبی
    daily_subscription_fee: Mapped[int] = mapped_column(Integer, default=0)
    
    # ساختار سلسله‌مراتبی (Sub-Reseller)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("resellers.id"), nullable=True)
    can_create_sub: Mapped[bool] = mapped_column(Boolean, default=False) # آیا اجازه زیرمجموعه‌گیری دارد؟
    
    status: Mapped[ResellerStatus] = mapped_column(Enum(ResellerStatus), default=ResellerStatus.ACTIVE)
    api_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True) # برای اتصال ربات
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ارتباطات (Relations)
    allocations = relationship("NodeAllocation", back_populates="reseller")
    transactions = relationship("TransactionLog", back_populates="reseller")
    users = relationship("GuardinoUser", back_populates="reseller")

# ================= 2. جدول نودها (سرورهای مرزبان، پاسارگاد و ...) =================
class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100)) # مثلا: سرور VIP آلمان
    panel_type: Mapped[PanelType] = mapped_column(Enum(PanelType))
    api_url: Mapped[str] = mapped_column(String(255))
    api_token: Mapped[str] = mapped_column(Text)
    
    status: Mapped[NodeStatus] = mapped_column(Enum(NodeStatus), default=NodeStatus.ACTIVE)
    is_visible_in_sub: Mapped[bool] = mapped_column(Boolean, default=True) # حالت روح / مخفی در ساب
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    allocations = relationship("NodeAllocation", back_populates="node")

# ================= 3. جدول تخصیص نود و قیمت اختصاصی (ماتریس دسترسی) =================
class NodeAllocation(Base):
    __tablename__ = "node_allocations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reseller_id: Mapped[int] = mapped_column(ForeignKey("resellers.id"))
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"))
    
    # قیمت‌های اختصاصی (اگر نال باشد، از قیمت پایه نماینده استفاده می‌شود)
    custom_price_per_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    custom_price_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)

    reseller = relationship("Reseller", back_populates="allocations")
    node = relationship("Node", back_populates="allocations")

# ================= 4. جدول کاربران مرکزی گاردینو =================
class GuardinoUser(Base):
    __tablename__ = "guardino_users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reseller_id: Mapped[int] = mapped_column(ForeignKey("resellers.id"))
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE)
    
    purchased_data_limit: Mapped[int] = mapped_column(BigInteger) # به بایت
    expire_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    total_cost: Mapped[int] = mapped_column(Integer) # برای استرداد وجه دقیق
    sub_token: Mapped[str] = mapped_column(String(64), unique=True, index=True) # توکن لینک ساب یکپارچه
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    reseller = relationship("Reseller", back_populates="users")
    sub_accounts = relationship("SubAccount", back_populates="guardino_user", cascade="all, delete-orphan")

# ================= 5. جدول اکانت‌های زیرمجموعه (اتصال کاربر به نودهای واقعی) =================
class SubAccount(Base):
    __tablename__ = "sub_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    guardino_user_id: Mapped[int] = mapped_column(ForeignKey("guardino_users.id"))
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"))
    
    remote_identifier: Mapped[str] = mapped_column(String(255)) # UUID یا Username در پنل مقصد
    used_traffic: Mapped[int] = mapped_column(BigInteger, default=0) # سینک شده از مرزبان/پاسارگاد
    
    guardino_user = relationship("GuardinoUser", back_populates="sub_accounts")
    node = relationship("Node")

# ================= 6. جدول تاریخچه تراکنش‌ها =================
class TransactionLog(Base):
    __tablename__ = "transactions_log"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reseller_id: Mapped[int] = mapped_column(ForeignKey("resellers.id"))
    amount: Mapped[int] = mapped_column(Integer) # مثبت یا منفی
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    reseller = relationship("Reseller", back_populates="transactions")
