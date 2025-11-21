import asyncio
import logging, os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import BOT_TOKEN
from db.db_init import init_db

# Роутеры
from handlers import registration, pets, booking, common, notifications, appointments, calendar

# === Логирование ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# === Инициализация базы данных ===
init_db()
logging.info("✅ База данных успешно инициализирована.")

# === Настройка бота и диспетчера ===
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# === Подключение роутеров в правильном порядке ===
dp.include_router(registration.router)
dp.include_router(pets.router)
dp.include_router(booking.router)
dp.include_router(common.router)
dp.include_router(notifications.router)
dp.include_router(appointments.router)


async def on_startup(bot: Bot):
    # Удаляем вебхук если был установлен ранее
    await bot.delete_webhook()
    # Устанавливаем новый вебхук (для Railway это не обязательно, но оставляем для совместимости)
    # await bot.set_webhook(f"https://{os.getenv('RAILWAY_STATIC_URL')}.railway.app")


async def on_shutdown(bot: Bot):
    await bot.session.close()


async def main_webhook():
    """Запуск через вебхуки (рекомендуется для Railway)"""
    await on_startup(bot)

    # Запускаем фоновую задачу уведомлений
    asyncio.create_task(notifications.check_and_send_notifications(bot))

    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    return app


async def main_polling():
    """Запуск через поллинг (альтернативный вариант)"""
    logging.info("🚀 Бот запущен через поллинг")

    # Запускаем фоновую задачу уведомлений
    asyncio.create_task(notifications.check_and_send_notifications(bot))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logging.info("🛑 Бот остановлен")


if __name__ == "__main__":
    # Всегда используем поллинг (и в Railway и локально)
    asyncio.run(main_polling())
