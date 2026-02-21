# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import users, subscriptions, auth

# 1. ابتدا هسته API را می‌سازیم
app = FastAPI(
    title="Guardino Core API",
    description="Enterprise Multi-Panel VPN Aggregator and Billing System",
    version="1.0.0"
)

# 2. تنظیمات CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. اتصال روترها (فقط یک‌بار)
app.include_router(users.router)
app.include_router(subscriptions.router)
app.include_router(auth.router)

@app.get("/")
async def root():
    return {
        "status": "Online",
        "service": "Guardino Core Engine",
        "message": "Welcome to the Enterprise VPN Infrastructure."
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "unknown", "redis": "unknown"}
