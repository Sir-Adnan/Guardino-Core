# app/core/celery_app.py
from celery import Celery
from celery.schedules import crontab

# اتصال به دیتابیس Redis (که در docker-compose ساختیم)
celery_app = Celery(
    "guardino_worker",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
    include=['app.tasks.sync_worker']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tehran',
    enable_utc=True,
)

# زمان‌بندی تسک‌ها (Cron Jobs)
celery_app.conf.beat_schedule = {
    # هر 5 دقیقه مصرف همه کاربران را چک کن
    'sync-all-users-traffic-every-5-mins': {
        'task': 'app.tasks.sync_worker.sync_all_traffic',
        'schedule': crontab(minute='*/5'),
    },
    # هر شب ساعت 12 حق اشتراک روزانه نمایندگان را کسر کن
    'deduct-daily-fees-midnight': {
        'task': 'app.tasks.sync_worker.deduct_daily_fees',
        'schedule': crontab(hour=0, minute=0),
    },
}
