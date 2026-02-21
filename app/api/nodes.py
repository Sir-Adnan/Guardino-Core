# app/api/nodes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Node, Reseller, NodeAllocation
from app.api.deps import get_current_reseller
from app.schemas.admin import NodeCreate
from app.services.node_factory import NodeFactory

router = APIRouter(prefix="/api/v1/nodes", tags=["Nodes & Servers"])

@router.post("/add")
async def add_new_node(
    node_data: NodeCreate,
    current_admin: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    if current_admin.parent_id is not None:
        raise HTTPException(status_code=403, detail="فقط ادمین کل اجازه افزودن سرور دارد.")

    # 1. ساخت شیء موقت برای تست اتصال
    temp_node = Node(
        display_name=node_data.display_name,
        panel_type=node_data.panel_type,
        api_url=node_data.api_url,
        api_token=node_data.api_token
    )
    
    # 2. تست اتصال قبل از ذخیره در دیتابیس (جلوگیری از اضافه شدن سرور فیک)
    try:
        adapter = NodeFactory.get_adapter(temp_node)
        if hasattr(adapter, 'test_connection'):
            await adapter.test_connection()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail="عدم دسترسی به سرور. آدرس یا پورت را بررسی کنید.")

    # 3. ذخیره نهایی در صورت موفقیت
    new_node = Node(
        display_name=node_data.display_name,
        panel_type=node_data.panel_type,
        api_url=node_data.api_url,
        api_token=node_data.api_token,
        status=node_data.status,
        is_visible_in_sub=node_data.is_visible_in_sub
    )
    db.add(new_node)
    await db.commit()
    await db.refresh(new_node)
    return {"message": "سرور تایید شد و با موفقیت متصل گردید.", "node_id": new_node.id}

@router.get("/list")
async def list_available_nodes(
    current_reseller: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    if current_reseller.parent_id is None:
        result = await db.execute(select(Node).order_by(Node.id.desc()))
        nodes = result.scalars().all()
    else:
        stmt = select(Node).join(NodeAllocation).where(NodeAllocation.reseller_id == current_reseller.id)
        result = await db.execute(stmt)
        nodes = result.scalars().all()
        
    return {"nodes": nodes}

@router.delete("/{node_id}")
async def delete_node(
    node_id: int,
    current_admin: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    """حذف سرور (فقط برای ادمین)"""
    if current_admin.parent_id is not None:
        raise HTTPException(status_code=403, detail="عدم دسترسی")
        
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="سرور یافت نشد")
        
    await db.delete(node)
    await db.commit()
    return {"message": "سرور با موفقیت حذف شد."}

@router.put("/{node_id}/toggle")
async def toggle_node_status(
    node_id: int,
    current_admin: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    """خاموش/روشن کردن سرور"""
    if current_admin.parent_id is not None:
        raise HTTPException(status_code=403, detail="عدم دسترسی")
        
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="سرور یافت نشد")
        
    node.status = "offline" if node.status == "active" else "active"
    await db.commit()
    return {"message": f"وضعیت سرور به {node.status} تغییر یافت."}
