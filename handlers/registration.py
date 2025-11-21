# handlers/registration.py
from aiogram import Router, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from db.db_utils import get_user_by_telegram_id, add_user, add_pet
from handlers.common import main_menu_inline

router = Router()


# === Состояния FSM ===
class RegistrationState(StatesGroup):
    waiting_phone = State()
    waiting_pet_name = State()
    waiting_pet_species = State()
    waiting_pet_age = State()

WELCOME_TEXT = (
    "👋 Добро пожаловать в *Усы, лапы и хвост*! 🐾\n\n"
    "Мы заботимся о здоровье ваших питомцев и предлагаем полный спектр ветеринарных услуг:\n\n"
    "🩺 Консультации и приёмы опытных врачей - от 1200 рублей\n"
    "🐶 Лечение и уход за собаками, кошками и другими питомцами - от 300 рублей\n"
    "💉 Вакцинация, чипирование и профилактика заболеваний - от 800 рублей\n"
    "🧾 Удобная запись на приём прямо через Telegram-бота\n\n"
    "🌟 Наши преимущества:\n"
    "• Дружелюбная атмосфера и заботливый персонал\n"
    "• Современное оборудование и проверенные методики\n"
    "• Напоминания о приёме и удобный доступ к вашим питомцам\n\n"
)

@router.message(F.text == "/start")
async def start_command(message: types.Message, state: FSMContext):
    user = get_user_by_telegram_id(message.from_user.id)

    # --- Отправляем рекламное приветственное сообщение ---
    sent_welcome = await message.answer(WELCOME_TEXT)

    # Сохраняем ID приветственного сообщения в state
    await state.update_data(
        welcome_message_id=sent_welcome.message_id,
        sent_messages=[sent_welcome.message_id]  # список всех сообщений бота
    )

    if user:
        # Пользователь уже зарегистрирован
        sent_menu = await message.answer(
            f"👋 С возвращением, {user[3] or message.from_user.full_name}! "
            "Выберите действие ниже, чтобы начать пользоваться ботом 🏥",
            reply_markup=main_menu_inline()
        )
        # Добавляем меню в список сообщений
        data = await state.get_data()
        messages = data.get("sent_messages", [])
        messages.append(sent_menu.message_id)
        await state.update_data(sent_messages=messages)
        return

    # --- Новая регистрация — запрос телефона ---
    contact_btn = KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)
    kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[contact_btn]])
    sent_phone_request = await message.answer(
        "Пожалуйста, поделитесь вашим номером телефона, чтобы мы могли зарегистрировать вас:",
        reply_markup=kb
    )
    # Добавляем в список сообщений
    data = await state.get_data()
    messages = data.get("sent_messages", [])
    messages.append(sent_phone_request.message_id)
    await state.update_data(sent_messages=messages)

    await state.set_state(RegistrationState.waiting_phone)

# === Получаем номер телефона ===
@router.message(RegistrationState.waiting_phone, F.contact)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    full_name = message.from_user.full_name

    add_user(telegram_id=message.from_user.id, phone=phone, full_name=full_name)

    await state.update_data(phone=phone, full_name=full_name)
    await state.set_state(RegistrationState.waiting_pet_name)

    await message.answer("🐾 Теперь добавим вашего питомца!\nВведите имя питомца:", reply_markup=types.ReplyKeyboardRemove())


# === Имя питомца ===
@router.message(RegistrationState.waiting_pet_name)
async def pet_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("⚠️ Имя не может быть пустым. Введите имя питомца.")
        return

    await state.update_data(pet_name=name)
    await state.set_state(RegistrationState.waiting_pet_species)
    await message.answer("🐶 Укажите вид питомца (например: кошка, собака):")


# === Вид питомца ===
@router.message(RegistrationState.waiting_pet_species)
async def pet_species(message: types.Message, state: FSMContext):
    species = message.text.strip()
    if not species:
        await message.answer("⚠️ Укажите вид питомца (например: кошка, собака).")
        return

    await state.update_data(pet_species=species)
    await state.set_state(RegistrationState.waiting_pet_age)
    await message.answer("🕐 Укажите возраст питомца (в годах, можно дробно):")


# === Возраст питомца ===
@router.message(RegistrationState.waiting_pet_age)
async def pet_age(message: types.Message, state: FSMContext):
    age_text = message.text.strip()
    age = None
    if age_text:
        try:
            _ = float(age_text.replace(",", "."))
            age = age_text
        except Exception:
            await message.answer("⚠️ Некорректный формат возраста. Введите число (например: 3 или 2.5) или оставьте пустым.")
            return

    data = await state.get_data()
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❗ Ошибка регистрации. Попробуйте снова /start.")
        await state.clear()
        return

    add_pet(
        user_id=user[0],
        name=data.get("pet_name"),
        species=data.get("pet_species"),
        age=age
    )

    await state.clear()

    await message.answer(
        f"✅ Регистрация завершена!\nПитомец {data.get('pet_name')} ({data.get('pet_species')}) успешно добавлен!",
        reply_markup=main_menu_inline()
    )

