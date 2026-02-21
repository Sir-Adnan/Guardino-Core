# app/tasks/sync_worker.py
import asyncio
from app.core.celery_app import celery_app
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.models import GuardinoUser, UserStatus, SubAccount, Reseller, TransactionLog, TransactionType
from app.services.node_factory import NodeFactory

async def _async_sync_traffic():
    """هسته اصلی چک کردن ترافیک (غیرهمگام)"""
    async with AsyncSessionLocal() as db:
        # پیدا کردن تمام کاربرانی که وضعیتشان Active است
        query = await db.execute(
            select(GuardinoUser)
            .where(GuardinoUser.status == UserStatus.ACTIVE)
            .options(selectinload(GuardinoUser.sub_accounts).selectinload(SubAccount.node))
        )
        active_users = query.scalars().all()

        for user in active_users:
            total_used_bytes = 0
            
            # چک کردن مصرف این کاربر در تک‌تک سرورهای متصل به آن
            for sub_acc in user.sub_accounts:
                if sub_acc.node.status != "active":
                    continue
                    
                try:
                    adapter = NodeFactory.get_adapter(sub_acc.node)
                    # دریافت اطلاعات کاربر از پنل بومی
                    remote_user_data = await adapter.get_user(sub_acc.remote_identifier)
                    
                    # استخراج مصرف بر اساس نوع پنل
                    used_traffic = 0
                    if sub_acc.node.panel_type == "marzban":
                        used_traffic = remote_user_data.get("used_traffic", 0)
                    elif sub_acc.node.panel_type == "pasarguard":
                        used_traffic = remote_user_data.get("used_traffic", 0) # فرض بر تشابه فیلد
                        
                    # آپدیت آخرین مصرفِ این ساب‌اکانت در دیتابیس خودمان
                    sub_acc.used_traffic = used_traffic
                    total_used_bytes += used_traffic
                    
                except Exception as e:
                    print(f"Error fetching usage for {user.username} from node {sub_acc.node.id}: {e}")

            # بررسی اینکه آیا مجموع مصرف از حجم خریداری شده بیشتر شده است؟
            if total_used_bytes >= user.purchased_data_limit:
                # 1. تغییر وضعیت در گاردینو
                user.status = UserStatus.DISABLED
                
                # 2. ارسال دستور مسدودی به تمام نودهای متصل
                for sub_acc in user.sub_accounts:
                    if sub_acc.node.status == "active":
                        try:
                            adapter = NodeFactory.get_adapter(sub_acc.node)
                            await adapter.suspend_user(sub_acc.remote_identifier)
                        except Exception as e:
                            print(f"Failed to suspend {user.username} on node {sub_acc.node.id}: {e}")
                            
        await db.commit()

@celery_app.task
def sync_all_traffic():
    """تسک زمان‌بندی شده برای چک کردن ترافیک که توسط Celery Beat صدا زده می‌شود"""
    asyncio.run(_async_sync_traffic())
    return "Traffic sync completed."


async def _async_deduct_fees():
    """کسر حق اشتراک روزانه نمایندگان"""
    async with AsyncSessionLocal() as db:
        query = await db.execute(select(Reseller).where(Reseller.daily_subscription_fee > 0))
        resellers = query.scalars().all()
        
        for reseller in resellers:
            reseller.balance -= reseller.daily_subscription_fee
            
            log = TransactionLog(
                reseller_id=reseller.id,
                amount=-reseller.daily_subscription_fee,
                transaction_type=TransactionType.DAILY_FEE,
                description="کسر حق اشتراک روزانه نگهداری پنل"
            )
            db.add(log)
            
            # اگر موجودی منفی شد، پنل نماینده قفل می‌شود
            if reseller.balance < 0 and reseller.status == "active":
                reseller.status = "locked"
                
        await db.commit()

@celery_app.task
def deduct_daily_fees():
    asyncio.run(_async_deduct_fees())
    return "Daily fees deducted."
