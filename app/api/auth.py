# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models import Reseller

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/login")
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    دریافت نام کاربری و رمز عبور و بازگرداندن توکن JWT
    """
    # جستجوی نماینده
    query = await db.execute(select(Reseller).where(Reseller.username == form_data.username))
    reseller = query.scalar_one_or_none()
    
    # بررسی صحت نماینده و رمز عبور
    if not reseller or not verify_password(form_data.password, reseller.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است.",
        )
        
    if reseller.status == "suspended":
        raise HTTPException(status_code=403, detail="اکانت شما مسدود شده است.")

    # ساخت توکن
    access_token = create_access_token(subject=reseller.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "reseller_id": reseller.id,
        "balance": reseller.balance,
        "role": "master" if reseller.parent_id is None else "sub"
    }
