# app/api/nodes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Node, Reseller, NodeAllocation
from app.api.deps import get_current_reseller
from app.schemas.admin import NodeCreate

router = APIRouter(prefix="/api/v1/nodes", tags=["Nodes & Servers"])

@router.post("/add")
async def add_new_node(
    node_data: NodeCreate,
    current_admin: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    # فقط ادمین کل می‌تواند سرور فیزیکی اضافه کند
    if current_admin.parent_id is not None:
        raise HTTPException(status_code=403, detail="فقط ادمین کل اجازه افزودن سرور دارد.")

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
    
    return {"message": "سرور با موفقیت به گاردینو متصل شد.", "node_id": new_node.id}

@router.get("/list")
async def list_available_nodes(
    current_reseller: Reseller = Depends(get_current_reseller),
    db: AsyncSession = Depends(get_db)
):
    """
    دریافت لیست سرورها (ادمین همه را می‌بیند، نماینده فقط مجازها را)
    """
    if current_reseller.parent_id is None:
        # ادمین کل
        result = await db.execute(select(Node))
        nodes = result.scalars().all()
    else:
        # نماینده: اتصال جدول Node و NodeAllocation برای فیلتر کردن
        stmt = select(Node).join(NodeAllocation).where(NodeAllocation.reseller_id == current_reseller.id)
        result = await db.execute(stmt)
        nodes = result.scalars().all()
        
    return {"nodes": nodes}
