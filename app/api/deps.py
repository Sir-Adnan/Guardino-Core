# app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import ALGORITHM
from app.models import Reseller

# این آدرس API لاگین ما خواهد بود
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_reseller(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> Reseller:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="توکن نامعتبر است یا منقضی شده است.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # رمزگشایی توکن
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        reseller_id: str = payload.get("sub")
        if reseller_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # پیدا کردن نماینده در دیتابیس
    query = await db.execute(select(Reseller).where(Reseller.id == int(reseller_id)))
    reseller = query.scalar_one_or_none()
    
    if reseller is None:
        raise credentials_exception
        
    if reseller.status == "suspended":
        raise HTTPException(status_code=403, detail="اکانت شما مسدود شده است.")
        
    return reseller
