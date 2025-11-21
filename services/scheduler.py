from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import asyncio

async def send_reminders(bot):
    now = datetime.now().strftime("%H:%M:%S")
    await bot.send_message(
        chat_id=123456789,  # 🔸 временно можно подставить свой Telegram ID
        text=f"🔔 Тестовое напоминание — {now}"
    )

def setup_scheduler(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_reminders, "interval", minutes=30, args=(bot,))
    scheduler.start()
