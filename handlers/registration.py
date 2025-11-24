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


# Клавиатура для выбора вида питомца
def get_species_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐱 Кот", callback_data="reg_species_Кот"),
         InlineKeyboardButton(text="🐶 Собака", callback_data="reg_species_Собака")],
        [InlineKeyboardButton(text="🐹 Грызун", callback_data="reg_species_Грызун"),
         InlineKeyboardButton(text="🦎 Рептилия", callback_data="reg_species_Рептилия")],
        [InlineKeyboardButton(text="🦜 Птица", callback_data="reg_species_Птица"),
         InlineKeyboardButton(text="❓ Другой", callback_data="reg_species_Другой")]
    ])


# Клавиатура для выбора возраста
def get_age_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍼 0-1 год", callback_data="reg_age_0-1 год")],
        [InlineKeyboardButton(text="🐕 1-5 лет", callback_data="reg_age_1-5 лет")],
        [InlineKeyboardButton(text="🐾 5-10 лет", callback_data="reg_age_5-10 лет")],
        [InlineKeyboardButton(text="🦴 10-15 лет", callback_data="reg_age_10-15 лет")],
        [InlineKeyboardButton(text="🌟 15+ лет", callback_data="reg_age_15+ лет")]
    ])


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

    await message.answer("🐾 Теперь добавим вашего питомца!\nВведите имя питомца:",
                         reply_markup=types.ReplyKeyboardRemove())


# === Имя питомца ===
@router.message(RegistrationState.waiting_pet_name)
async def pet_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("⚠️ Имя не может быть пустым. Введите имя питомца.")
        return

    await state.update_data(pet_name=name)
    await state.set_state(RegistrationState.waiting_pet_species)

    # Используем инлайн-кнопки для выбора вида
    await message.answer(
        "🐾 Выберите вид питомца:",
        reply_markup=get_species_keyboard()
    )


# === Обработка выбора вида питомца (инлайн-кнопки) ===
@router.callback_query(RegistrationState.waiting_pet_species, F.data.startswith("reg_species_"))
async def pet_species_selected(callback: types.CallbackQuery, state: FSMContext):
    species = callback.data.split("_", 2)[2]  # Получаем вид после "reg_species_"

    await state.update_data(pet_species=species)
    await state.set_state(RegistrationState.waiting_pet_age)

    # Предлагаем выбрать возраст через инлайн-кнопки
    await callback.message.edit_text(
        f"✅ Выбран вид: {species}\n\n🕐 Теперь выберите возраст питомца:",
        reply_markup=get_age_keyboard()
    )
    await callback.answer()


# === Обработка выбора возраста (инлайн-кнопки) ===
@router.callback_query(RegistrationState.waiting_pet_age, F.data.startswith("reg_age_"))
async def pet_age_selected(callback: types.CallbackQuery, state: FSMContext):
    age = callback.data.split("_", 2)[2]  # Получаем возраст после "reg_age_"

    data = await state.get_data()
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("❗ Ошибка регистрации. Попробуйте снова /start.")
        await state.clear()
        return

    # Добавляем питомца в базу
    add_pet(
        user_id=user[0],
        name=data.get('pet_name'),
        species=data.get('pet_species'),
        age=age
    )

    await state.clear()

    await callback.message.edit_text(
        f"✅ Регистрация завершена!\n\n"
        f"🐾 Питомец: {data.get('pet_name')}\n"
        f"📋 Вид: {data.get('pet_species')}\n"
        f"🕐 Возраст: {age}\n\n"
        f"Теперь вы можете записаться на приём!",
        reply_markup=main_menu_inline()
    )
    await callback.answer()
