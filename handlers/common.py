from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.fsm.context import FSMContext

router = Router()

# Главное меню через inline-кнопки
def main_menu_inline():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐾 Мои питомцы", callback_data="my_pets")],
        [InlineKeyboardButton(text="📅 Записаться к врачу", callback_data="book_visit")],
        [InlineKeyboardButton(text="🧾 Мои записи", callback_data="my_appointments")],
    ])


# === Приветствие / старт ===
@router.message(F.text.in_({"/start", "/menu"}))
async def start_message(message: Message, state: FSMContext):
    await state.clear()
    user_name = message.from_user.full_name or message.from_user.username or "друг"
    await message.answer(
        f"🐾 Привет, {user_name}!\nВыберите действие ниже:",
        reply_markup=main_menu_inline()
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    welcome_id = data.get("welcome_message_id")
    sent_messages = data.get("sent_messages", [])

    # Удаляем все предыдущие сообщения бота, кроме приветствия
    for msg_id in sent_messages:
        if msg_id != welcome_id:
            try:
                await callback.message.bot.delete_message(chat_id=callback.from_user.id, message_id=msg_id)
            except:
                pass  # если сообщение уже удалено или нельзя удалить, игнорируем

    # Сбрасываем список сообщений, оставляем только приветствие
    await state.update_data(sent_messages=[welcome_id])

    # Отправляем новое главное меню
    try:
        sent_menu = await callback.message.edit_text("🏠 Главное меню:", reply_markup=main_menu_inline())
    except:
        sent_menu = await callback.message.answer("🏠 Главное меню:", reply_markup=main_menu_inline())

    # Добавляем ID нового меню в список сообщений
    data = await state.get_data()
    messages = data.get("sent_messages", [])
    messages.append(sent_menu.message_id)
    await state.update_data(sent_messages=messages)

    await callback.answer()

async def add_message_to_state(message, state):
    data = await state.get_data()
    messages = data.get("sent_messages", [])
    messages.append(message.message_id)
    await state.update_data(sent_messages=messages)

async def delete_previous_messages(message, state, keep_ids=[]):
    data = await state.get_data()
    messages = data.get("sent_messages", [])

    for msg_id in messages:
        if msg_id not in keep_ids:
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
            except Exception:
                pass  # сообщение могло быть уже удалено

    remaining = [mid for mid in messages if mid in keep_ids]
    await state.update_data(sent_messages=remaining)
