# app/api/resellers.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_password_hash
from app.models import Reseller, NodeAllocation, TransactionLog
from app.api.deps import get_current_reseller
from app.schemas.admin import ResellerCreate, NodeAllocationCreate

router = APIRouter(prefix="/api/v1/resellers", tags=["Resellers Management"])

@router.post("/create")
async def create_reseller(
    data: ResellerCreate,
    current_reseller: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    # آیا این شخص اجازه دارد زیرمجموعه بگیرد؟
    if not current_reseller.can_create_sub and current_reseller.parent_id is not None:
        raise HTTPException(status_code=403, detail="شما اجازه ساخت زیرمجموعه را ندارید.")

    # چک کردن تکراری نبودن یوزرنیم
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
    """تخصیص یک سرور به نماینده زیرمجموعه با قیمت دلخواه"""
    allocation = NodeAllocation(
        reseller_id=reseller_id,
        node_id=data.node_id,
        custom_price_per_gb=data.custom_price_per_gb,
        custom_price_per_day=data.custom_price_per_day
    )
    
    db.add(allocation)
    await db.commit()
    return {"message": "سرور با موفقیت به نماینده تخصیص داده شد."}

# ---> این بخش اصلاح شد (فاصله‌های اضافی حذف شدند) <---
@router.get("/history")
async def get_financial_history(
    current_reseller: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    """دریافت ۵۰ تراکنش آخر نماینده"""
    query = await db.execute(
        select(TransactionLog)
        .where(TransactionLog.reseller_id == current_reseller.id)
        .order_by(TransactionLog.created_at.desc())
        .limit(50)
    )
    logs = query.scalars().all()
    
    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "amount": log.amount,
            "type": log.transaction_type.value, # اضافه شدن .value برای تبدیل Enum به متن
            "description": log.description,
            "date": log.created_at.isoformat()
        })
        
    return {"history": result}
