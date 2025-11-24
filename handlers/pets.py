# handlers/pets.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from db.db_utils import get_user_by_telegram_id, get_user_pets, add_pet, connect
from handlers.common import main_menu_inline

router = Router()

# === Состояния FSM для добавления питомца ===
class PetState(StatesGroup):
    waiting_name = State()
    waiting_species = State()
    waiting_age = State()

# Клавиатура для выбора вида питомца
def get_species_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐱 Кот", callback_data="species_Кот"),
         InlineKeyboardButton(text="🐶 Собака", callback_data="species_Собака")],
        [InlineKeyboardButton(text="🐹 Грызун", callback_data="species_Грызун"),
         InlineKeyboardButton(text="🦎 Рептилия", callback_data="species_Рептилия")],
        [InlineKeyboardButton(text="🦜 Птица", callback_data="species_Птица"),
         InlineKeyboardButton(text="❓ Другой", callback_data="species_Другой")]
    ])

# Клавиатура для выбора возраста
def get_age_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍼 0-1 год", callback_data="age_0-1 год")],
        [InlineKeyboardButton(text="🐕 1-5 лет", callback_data="age_1-5 лет")],
        [InlineKeyboardButton(text="🐾 5-10 лет", callback_data="age_5-10 лет")],
        [InlineKeyboardButton(text="🦴 10-15 лет", callback_data="age_10-15 лет")],
        [InlineKeyboardButton(text="🌟 15+ лет", callback_data="age_15+ лет")]
    ])

# === Клавиатура питомцев ===
def pets_keyboard(pets):
    kb = []
    for pet in pets:
        pet_id, name, species, age = pet
        kb.append([InlineKeyboardButton(text=f"❌ Удалить {name}", callback_data=f"delete_pet_{pet_id}")])
    kb.append([InlineKeyboardButton(text="➕ Добавить питомца", callback_data="add_pet")])
    kb.append([InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# === Просмотр питомцев ===
@router.callback_query(F.data == "my_pets")
async def show_my_pets(callback: CallbackQuery):
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("❗ Вы не зарегистрированы. Введите /start.")
        await callback.answer()
        return

    pets = get_user_pets(user[0])
    if not pets:
        text = "🐾 У вас пока нет питомцев."
    else:
        text = "🐾 Ваши питомцы:\n\n"
        for p in pets:
            text += f"• {p[1]} ({p[2] or 'вид не указан'}, {p[3] or 'возраст не указан'})\n"

    kb = pets_keyboard(pets)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

# === Удаление питомца ===
@router.callback_query(F.data.startswith("delete_pet_"))
async def delete_pet(callback: CallbackQuery):
    pet_id = int(callback.data.split("_")[-1])
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.")
        return

    with connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM pets WHERE id=? AND user_id=?", (pet_id, user[0]))
        conn.commit()

    pets = get_user_pets(user[0])
    if not pets:
        text = "🐾 У вас больше нет питомцев."
    else:
        text = "🐾 Ваши питомцы:\n\n"
        for p in pets:
            text += f"• {p[1]} ({p[2] or 'вид не указан'}, {p[3] or 'возраст не указан'})\n"

    kb = pets_keyboard(pets)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer("✅ Питомец удалён.")

# === Добавление питомца ===
@router.callback_query(F.data == "add_pet")
async def add_pet_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetState.waiting_name)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Отмена", callback_data="cancel_pet_add")]
    ])

    await callback.message.edit_text("🐶 Как зовут вашего питомца?\n\n(введите имя в сообщении)", reply_markup=kb)
    await callback.answer()

@router.message(StateFilter(PetState.waiting_name))
async def pet_name_entered(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("⚠️ Имя не может быть пустым. Введите имя питомца.")
        return

    await state.update_data(pet_name=name)
    await state.set_state(PetState.waiting_species)

    await message.answer("🐾 Выберите вид питомца:", reply_markup=get_species_keyboard())

# === Выбор вида ===
@router.callback_query(StateFilter(PetState.waiting_species), F.data.startswith("species_"))
async def pet_species_selected(callback: CallbackQuery, state: FSMContext):
    species = callback.data.split("_", 1)[1]
    await state.update_data(pet_species=species)
    await state.set_state(PetState.waiting_age)

    await callback.message.edit_text(
        f"✅ Выбран вид: {species}\n\n🕐 Теперь выберите возраст питомца:",
        reply_markup=get_age_keyboard()
    )
    await callback.answer()

# === Выбор возраста ===
@router.callback_query(StateFilter(PetState.waiting_age), F.data.startswith("age_"))
async def pet_age_selected(callback: CallbackQuery, state: FSMContext):
    age = callback.data.split("_", 1)[1]

    data = await state.get_data()
    pet_name = data.get("pet_name")
    pet_species = data.get("pet_species")

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("❗ Пользователь не найден. Введите /start.")
        await state.clear()
        return

    add_pet(user_id=user[0], name=pet_name, species=pet_species, age=age)
    await state.clear()

    pets = get_user_pets(user[0])
    text = "🐾 Ваши питомцы:\n\n"
    for p in pets:
        text += f"• {p[1]} ({p[2] or 'вид не указан'}, {p[3] or 'возраст не указан'})\n"

    kb = pets_keyboard(pets)
    await callback.message.edit_text(
        f"✅ Питомец {pet_name} ({pet_species}, {age}) добавлен!\n\n{text}",
        reply_markup=kb
    )
    await callback.answer()

# === Кнопка "Назад" и "Отмена" ===
@router.callback_query(F.data == "back_to_name")
async def back_to_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetState.waiting_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Отмена", callback_data="cancel_pet_add")]
    ])
    await callback.message.edit_text("🐶 Как зовут вашего питомца? (введите имя)", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "back_to_species")
async def back_to_species(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetState.waiting_species)
    await callback.message.edit_text("🐾 Выберите вид питомца:", reply_markup=get_species_keyboard())
    await callback.answer()

@router.callback_query(F.data == "cancel_pet_add")
async def cancel_pet_add(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Добавление питомца отменено.", reply_markup=main_menu_inline())
    await callback.answer("Действие отменено.")