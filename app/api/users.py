# app/api/users.py
import asyncio
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Reseller, Node, NodeAllocation, GuardinoUser, SubAccount, TransactionLog, TransactionType, UserStatus
from app.schemas.user import UserCreateRequest, UserCreateResponse
from app.services.node_factory import NodeFactory
from app.api.deps import get_current_reseller

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

@router.post("/create", response_model=UserCreateResponse)
async def create_multi_node_user(
    request: UserCreateRequest,
    current_reseller: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    gb_to_bytes = 1073741824
    data_limit_bytes = int(request.data_limit_gb * gb_to_bytes)
    expire_timestamp = int((datetime.utcnow() + timedelta(days=request.expire_days)).timestamp()) if request.expire_days > 0 else 0

    # 1. قفل کردن کیف پول نماینده
    reseller_query = await db.execute(
        select(Reseller).where(Reseller.id == current_reseller.id).with_for_update()
    )
    reseller = reseller_query.scalar_one_or_none()
    if not reseller or reseller.status != "active":
        raise HTTPException(status_code=400, detail="نماینده یافت نشد یا مسدود است.")

    # 2. بررسی تکراری نبودن نام کاربری در گاردینو
    existing_user = await db.execute(select(GuardinoUser).where(GuardinoUser.username == request.username))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="این نام کاربری از قبل وجود دارد.")

    # 3. محاسبه هزینه ترکیبی از روی جداول دسترسی
    total_cost = 0
    valid_nodes = []
    
    for n_id in request.node_ids:
        # اصلاح شد: NodeAllocation.reseller_id صحیح است
        alloc_query = await db.execute(
            select(NodeAllocation).options(selectinload(NodeAllocation.node)).where(
                NodeAllocation.reseller_id == current_reseller.id,
                NodeAllocation.node_id == n_id
            )
        )
        allocation = alloc_query.scalar_one_or_none()
        
        if not allocation or allocation.node.status != "active":
            raise HTTPException(status_code=400, detail=f"شما به سرور {n_id} دسترسی ندارید یا سرور خاموش است.")
        
        price_gb = allocation.custom_price_per_gb if allocation.custom_price_per_gb is not None else reseller.base_price_master_sub
        price_day = allocation.custom_price_per_day if allocation.custom_price_per_day is not None else 0
        
        cost_for_this_node = (request.data_limit_gb * price_gb) + (request.expire_days * price_day)
        total_cost += int(cost_for_this_node)
        valid_nodes.append(allocation.node)

    # 4. بررسی موجودی کیف پول
    if reseller.balance < total_cost:
        raise HTTPException(status_code=400, detail=f"موجودی ناکافی. مبلغ مورد نیاز: {total_cost} تومان")

    # 5. ساخت کاربر در سرورها به صورت موازی (Async Parallel)
    creation_tasks = []
    for node in valid_nodes:
        adapter = NodeFactory.get_adapter(node)
        if node.panel_type == "marzban":
            task = adapter.create_user(request.username, expire_timestamp, data_limit_bytes, request.proxies, {"vless": ["vless-inbound"]})
        elif node.panel_type == "pasarguard":
            task = adapter.create_user(request.username, expire_timestamp, data_limit_bytes, request.proxy_settings)
        elif node.panel_type == "wgdashboard":
            task = adapter.create_user(request.username)
        creation_tasks.append(task)

    results = await asyncio.gather(*creation_tasks, return_exceptions=True)

    # 6. بررسی خطا و سیستم Rollback
    successful_nodes = []
    failed = False
    
    for i, result in enumerate(results):
        if isinstance(result, Exception) or (isinstance(result, dict) and "detail" in result):
            failed = True
            break
        successful_nodes.append(valid_nodes[i])

    if failed:
        rollback_tasks = []
        for snode in successful_nodes:
            adapter = NodeFactory.get_adapter(snode)
            rollback_tasks.append(adapter.delete_user(request.username))
        if rollback_tasks:
            await asyncio.gather(*rollback_tasks, return_exceptions=True)
            
        raise HTTPException(status_code=502, detail="خطا در ارتباط با یکی از سرورها. عملیات به طور کامل لغو شد و پولی کسر نگردید.")

    # 7. کسر موجودی و ثبت در دیتابیس
    reseller.balance -= total_cost
    
    expire_dt = datetime.utcnow() + timedelta(days=request.expire_days) if request.expire_days > 0 else None
    sub_token = uuid.uuid4().hex

    # اصلاح شد: reseller_id صحیح است
    new_user = GuardinoUser(
        reseller_id=current_reseller.id,
        username=request.username,
        status=UserStatus.ACTIVE,
        purchased_data_limit=data_limit_bytes,
        expire_date=expire_dt,
        total_cost=total_cost,
        sub_token=sub_token
    )
    db.add(new_user)
    await db.flush()

    for snode in valid_nodes:
        sub_acc = SubAccount(
            guardino_user_id=new_user.id,
            node_id=snode.id,
            remote_identifier=request.username
        )
        db.add(sub_acc)

    # اصلاح شد: reseller_id صحیح است
    log = TransactionLog(
        reseller_id=current_reseller.id,
        amount=-total_cost,
        transaction_type=TransactionType.BUY_VPN,
        description=f"ساخت کاربر {request.username} روی {len(valid_nodes)} سرور"
    )
    db.add(log)

    await db.commit()

    master_sub_link = f"https://sub.guardino.dev/sub/{sub_token}"

    return UserCreateResponse(
        message="✅ کاربر با موفقیت در تمام سرورها ساخته شد.",
        username=request.username,
        total_cost=total_cost,
        sub_link=master_sub_link
    )
