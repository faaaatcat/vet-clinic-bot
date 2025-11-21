import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Router
from aiogram.types import Message
from db.db_utils import connect

router = Router()

# === Получение предстоящих приёмов ===
def get_upcoming_appointments():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                a.id,
                u.telegram_id,
                p.name AS pet_name,
                d.full_name AS doctor_name,
                s.name AS service_name,
                sch.date,
                sch.time,
                a.notified_24h,
                a.notified_2h
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            JOIN pets p ON a.pet_id = p.id
            JOIN doctors d ON a.doctor_id = d.id
            JOIN services s ON a.service_id = s.id
            JOIN schedule sch ON a.schedule_id = sch.id
            WHERE a.status = 'scheduled'
        """)
        return cur.fetchall()

# === Проверка и отправка уведомлений ===
async def check_and_send_notifications(bot):
    now = datetime.now()
    upcoming = get_upcoming_appointments()

    for appt in upcoming:
        (
            appointment_id,
            telegram_id,
            pet_name,
            doctor_name,
            service_name,
            appt_date,
            appt_time,
            notified_24h,
            notified_2h
        ) = appt

        try:
            appt_datetime = datetime.strptime(f"{appt_date} {appt_time}", "%Y-%m-%d %H:%M")
        except Exception:
            continue

        time_until = appt_datetime - now

        # === За 24 часа ===
        if timedelta(hours=23, minutes=50) < time_until < timedelta(hours=24, minutes=10) and not notified_24h:
            await bot.send_message(
                telegram_id,
                f"📅 Напоминание!\n"
                f"Через сутки у вас приём:\n\n"
                f"🐾 Питомец: {pet_name}\n"
                f"👩‍⚕️ Врач: {doctor_name}\n"
                f"🧾 Услуга: {service_name}\n"
                f"🕓 Время: {appt_time} ({appt_date})"
            )
            mark_notified(appointment_id, "24h")

        # === За 2 часа ===
        elif timedelta(hours=1, minutes=50) < time_until < timedelta(hours=2, minutes=10) and not notified_2h:
            await bot.send_message(
                telegram_id,
                f"⏰ Напоминание!\n"
                f"Через 2 часа у вас приём:\n\n"
                f"🐾 Питомец: {pet_name}\n"
                f"👩‍⚕️ Врач: {doctor_name}\n"
                f"🧾 Услуга: {service_name}\n"
                f"🕓 Время: {appt_time} ({appt_date})"
            )
            mark_notified(appointment_id, "2h")

# === Пометка об отправке ===
def mark_notified(appointment_id: int, kind: str):
    with connect() as conn:
        cur = conn.cursor()
        if kind == "24h":
            cur.execute("UPDATE appointments SET notified_24h = 1 WHERE id = ?", (appointment_id,))
        elif kind == "2h":
            cur.execute("UPDATE appointments SET notified_2h = 1 WHERE id = ?", (appointment_id,))
        conn.commit()

# === Фоновая задача ===
async def notifications_scheduler(bot):
    logging.info("🔔 Система уведомлений запущена...")
    while True:
        await check_and_send_notifications(bot)
        await asyncio.sleep(300)  # каждые 5 минут

# === Ручная проверка (для теста) ===
@router.message(lambda msg: msg.text == "/check_notifications")
async def manual_check(message: Message):
    await check_and_send_notifications(message.bot)
    await message.answer("🔍 Проверка уведомлений выполнена.")
