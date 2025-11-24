from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import date
from db.db_utils import get_user_by_telegram_id, get_user_appointments, cancel_appointment
from handlers.common import main_menu_inline

router = Router()


# --- Универсальная клавиатура для списка записей ---
def appointments_kb(appointments):
    buttons = []
    for a in appointments:
        appointment_id = a[0]
        buttons.append([InlineKeyboardButton(text=f"❌ Отменить: {a[6]} ({a[3]} {a[4]})", callback_data=f"cancel_appointment_{appointment_id}")])
    buttons.append([InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Показать актуальные записи ---
@router.callback_query(F.data == "my_appointments")
async def show_my_appointments(callback: CallbackQuery):
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("❗ Вы не зарегистрированы. Введите /start.")
        await callback.answer()
        return

    appointments = get_user_appointments(user[0])
    today_iso = date.today().isoformat()

    # Фильтруем актуальные (сегодня и будущие)
    upcoming = [a for a in appointments if a[3] >= today_iso]

    if not upcoming:
        await callback.message.edit_text(
            "📅 У вас нет актуальных записей.",
            reply_markup=main_menu_inline()
        )
        await callback.answer()
        return

    # Собираем все записи в одно сообщение
    text_parts = []
    for a in upcoming:
        appointment_id, service_name, doctor_name, appt_date, appt_time, status, pet_name = a
        text_parts.append(
            f"🐾 <b>{pet_name}</b>\n"
            f"👩‍⚕️ <b>{doctor_name}</b>\n"
            f"🧾 {service_name}\n"
            f"📅 {appt_date} — {appt_time}\n"
            f"📌 Статус: <i>{status}</i>\n"
            "────────────────────"
        )

    text = "📋 <b>Ваши актуальные записи:</b>\n\n" + "\n\n".join(text_parts)

    await callback.message.edit_text(
        text,
        reply_markup=appointments_kb(upcoming),
        parse_mode="HTML"
    )

    await callback.answer()


# --- Обработка отмены записи ---
@router.callback_query(F.data.startswith("cancel_appointment_"))
async def cancel_appointment_handler(callback: CallbackQuery):
    appointment_id = int(callback.data.split("_")[-1])

    # Попытка удалить запись и освободить слот
    success = cancel_appointment(appointment_id, free_slot=True)

    if success:
        await callback.answer("✅ Запись отменена!", show_alert=False)

        # После удаления — обновляем список записей
        user = get_user_by_telegram_id(callback.from_user.id)
        appointments = get_user_appointments(user[0])
        today_iso = date.today().isoformat()
        upcoming = [a for a in appointments if a[3] >= today_iso]

        if upcoming:
            text_parts = []
            for a in upcoming:
                appointment_id, service_name, doctor_name, appt_date, appt_time, status, pet_name = a
                text_parts.append(
                    f"🐾 <b>{pet_name}</b>\n"
                    f"👩‍⚕️ <b>{doctor_name}</b>\n"
                    f"🧾 {service_name}\n"
                    f"📅 {appt_date} — {appt_time}\n"
                    f"📌 Статус: <i>{status}</i>\n"
                    "────────────────────"
                )
            text = "📋 <b>Ваши актуальные записи:</b>\n\n" + "\n\n".join(text_parts)
            await callback.message.edit_text(text, reply_markup=appointments_kb(upcoming), parse_mode="HTML")
        else:
            await callback.message.edit_text("📅 У вас больше нет актуальных записей.", reply_markup=main_menu_inline())

    else:
        await callback.answer("⚠️ Не удалось удалить запись.", show_alert=True)
