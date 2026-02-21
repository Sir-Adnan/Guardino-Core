# app/api/resellers.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_password_hash
from app.models import Reseller, NodeAllocation, TransactionLog, TransactionType
from app.api.deps import get_current_reseller
from app.schemas.admin import ResellerCreate, NodeAllocationCreate

router = APIRouter(prefix="/api/v1/resellers", tags=["Resellers Management"])

# --- اسکیما (مدل ورودی) برای شارژ کیف پول ---
class WalletChargeRequest(BaseModel):
    amount: int
    type: str # 'add' or 'sub'
    description: str = ""

@router.post("/create")
async def create_reseller(
    data: ResellerCreate,
    current_reseller: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    if not current_reseller.can_create_sub and current_reseller.parent_id is not None:
        raise HTTPException(status_code=403, detail="شما اجازه ساخت زیرمجموعه را ندارید.")

    query = await db.execute(select(Reseller).where(Reseller.username == data.username))
    if query.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="این نام کاربری قبلاً ثبت شده است.")

    new_reseller = Reseller(
        username=data.username,
        password_hash=get_password_hash(data.password),
        parent_id=current_reseller.id, 
        daily_subscription_fee=data.daily_subscription_fee,
        base_price_per_gb=max(data.base_price_per_gb, current_reseller.base_price_per_gb), 
        base_price_master_sub=max(data.base_price_master_sub, current_reseller.base_price_master_sub),
        can_create_sub=data.can_create_sub
    )
    db.add(new_reseller)
    await db.commit()
    return {"message": "نماینده با موفقیت ساخته شد."}

@router.post("/{reseller_id}/allocate-node")
async def allocate_node_to_reseller(
    reseller_id: int,
    data: NodeAllocationCreate,
    current_reseller: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    allocation = NodeAllocation(
        reseller_id=reseller_id, node_id=data.node_id,
        custom_price_per_gb=data.custom_price_per_gb, custom_price_per_day=data.custom_price_per_day
    )
    db.add(allocation)
    await db.commit()
    return {"message": "سرور به نماینده تخصیص داده شد."}

# -------- API دریافت لیست نمایندگان --------
@router.get("/list")
async def list_resellers(
    current_reseller: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    if current_reseller.parent_id is None:
        # ادمین کل همه نمایندگان را می‌بیند
        query = await db.execute(select(Reseller).where(Reseller.id != current_reseller.id).order_by(Reseller.id.desc()))
    else:
        # نماینده ارشد فقط زیرمجموعه‌های خودش را می‌بیند
        query = await db.execute(select(Reseller).where(Reseller.parent_id == current_reseller.id).order_by(Reseller.id.desc()))
        
    resellers = query.scalars().all()
    result = []
    for r in resellers:
        result.append({
            "id": r.id,
            "username": r.username,
            "balance": r.balance,
            "status": r.status.value,
            "price": r.base_price_per_gb
        })
    return {"resellers": result}

# -------- API شارژ کیف پول نمایندگان --------
@router.post("/{reseller_id}/charge")
async def charge_wallet(
    reseller_id: int,
    data: WalletChargeRequest,
    current_reseller: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    # بررسی دسترسی (آیا این شخص می‌تواند این نماینده را شارژ کند؟)
    target_query = await db.execute(select(Reseller).where(Reseller.id == reseller_id).with_for_update())
    target = target_query.scalar_one_or_none()
    
    if not target:
        raise HTTPException(status_code=404, detail="نماینده یافت نشد.")
        
    if current_reseller.parent_id is not None and target.parent_id != current_reseller.id:
        raise HTTPException(status_code=403, detail="شما فقط مجاز به شارژ زیرمجموعه‌های خود هستید.")

    # محاسبه مبلغ
    amount = data.amount if data.type == "add" else -data.amount
    
    # اعمال در دیتابیس
    target.balance += amount
    
    # ثبت لاگ مالی
    desc = data.description if data.description else ("شارژ توسط مدیر" if data.type == 'add' else "کسر توسط مدیر")
    log = TransactionLog(
        reseller_id=target.id,
        amount=amount,
        transaction_type=TransactionType.WALLET_CHARGE,
        description=desc
    )
    db.add(log)
    await db.commit()
    
    return {"message": "کیف پول با موفقیت بروزرسانی شد.", "new_balance": target.balance}

@router.get("/history")
async def get_financial_history(
    current_reseller: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    query = await db.execute(
        select(TransactionLog).where(TransactionLog.reseller_id == current_reseller.id).order_by(TransactionLog.created_at.desc()).limit(50)
    )
    logs = query.scalars().all()
    result = []
    for log in logs:
        result.append({
            "id": log.id, "amount": log.amount, "type": log.transaction_type.value,
            "description": log.description, "date": log.created_at.isoformat()
        })
    return {"history": result}
