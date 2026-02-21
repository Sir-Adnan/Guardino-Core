from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import users 
app.include_router(users.router)

app = FastAPI(
    title="Guardino Core API",
    description="Enterprise Multi-Panel VPN Aggregator and Billing System",
    version="1.0.0"
)

# تنظیمات CORS برای اتصال پنل فرانت‌اند (وب‌سایت) به این API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # در پروداکشن باید آدرس دامنه خودتان را بگذارید
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "status": "Online",
        "service": "Guardino Core Engine",
        "message": "Welcome to the Enterprise VPN Infrastructure."
    }

@app.get("/health")
async def health_check():
    # بعداً چک کردن اتصال دیتابیس و ردیس را اینجا اضافه می‌کنیم
    return {"status": "healthy", "database": "unknown", "redis": "unknown"}
