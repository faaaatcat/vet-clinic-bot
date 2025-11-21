# handlers/booking.py
from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.db_utils import (
    get_user_by_telegram_id,
    get_services,
    get_doctors_by_service,
    get_available_dates_for_doctor,
    get_available_slots_for_doctor_on_date,
    get_user_pets,
    book_slot
)
from handlers.common import main_menu_inline
from handlers.calendar import SimpleCalendar, SimpleCalendarCallback

router = Router()


# === FSM состояния ===
class BookingStates(StatesGroup):
    service = State()
    doctor = State()
    date = State()
    time = State()
    pet = State()


# === Вспомогательные строители клавиатур ===
def build_list_kb(items, footer_rows=None):
    """
    items: list of tuples (text, callback_data) -> каждая в своей строке
    footer_rows: list of rows, where each row is list of tuples (text, callback)
    Возвращает InlineKeyboardMarkup
    """
    kb_rows = []
    for txt, cb in items:
        kb_rows.append([InlineKeyboardButton(text=txt, callback_data=cb)])
    if footer_rows:
        for row in footer_rows:
            kb_rows.append([InlineKeyboardButton(text=t, callback_data=c) for (t, c) in row])
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


def nav_footer(back_cb: str = None):
    """Возвращает footer rows для build_list_kb"""
    footer = []
    if back_cb:
        footer.append(("🔙 Назад", back_cb))
    footer.append(("🏠 В меню", "back_to_menu"))
    return [footer]


# === Старт записи: выбираем услугу ===
@router.callback_query(F.data == "book_visit")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("❗ Вы не зарегистрированы. Введите /start, чтобы начать.")
        return

    services = get_services()
    if not services:
        await callback.message.answer("⚠️ Пока нет доступных услуг.")
        return

    items = [(f"{s[1]} — {s[3]}₽", f"choose_service_{s[0]}") for s in services]
    kb = build_list_kb(items, footer_rows=nav_footer())

    try:
        await callback.message.edit_text("🧾 Выберите услугу:", reply_markup=kb)
    except Exception:
        await callback.message.answer("🧾 Выберите услугу:", reply_markup=kb)

    await state.set_state(BookingStates.service)


# === Выбор услуги -> список врачей (фильтр по услуге) ===
@router.callback_query(BookingStates.service, F.data.startswith("choose_service_"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        service_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.message.answer("❌ Неправильный формат выбора услуги.")
        return

    await state.update_data(service_id=service_id)

    doctors = get_doctors_by_service(service_id)
    if not doctors:
        try:
            await callback.message.edit_text("⚠️ К сожалению, нет врачей, выполняющих эту услугу.")
        except Exception:
            await callback.message.answer("⚠️ К сожалению, нет врачей, выполняющих эту услугу.")
        return

    items = [(f"{d[1]} ({d[2] or 'специальность'})", f"choose_doctor_{d[0]}") for d in doctors]
    kb = build_list_kb(items, footer_rows=nav_footer("back_to_service"))

    try:
        await callback.message.edit_text("👩‍⚕️ Выберите врача (отфильтровано по услуге):", reply_markup=kb)
    except Exception:
        await callback.message.answer("👩‍⚕️ Выберите врача (отфильтровано по услуге):", reply_markup=kb)

    await state.set_state(BookingStates.doctor)


# === Назад к выбору услуги ===
@router.callback_query(BookingStates.doctor, F.data == "back_to_service")
async def back_to_service(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    services = get_services()
    items = [(f"{s[1]} — {s[3]}₽", f"choose_service_{s[0]}") for s in services]
    kb = build_list_kb(items, footer_rows=nav_footer())
    try:
        await callback.message.edit_text("🧾 Выберите услугу:", reply_markup=kb)
    except Exception:
        await callback.message.answer("🧾 Выберите услугу:", reply_markup=kb)
    await state.set_state(BookingStates.service)


# === Выбор врача -> даты ===
@router.callback_query(BookingStates.doctor, F.data.startswith("choose_doctor_"))
async def choose_doctor(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        doctor_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.message.answer("❌ Неправильный формат выбора врача.")
        return

    await state.update_data(doctor_id=doctor_id)

    dates = get_available_dates_for_doctor(doctor_id)
    if not dates:
        try:
            await callback.message.edit_text("⚠️ У этого врача нет доступных дат на ближайшие 2 недели.")
        except Exception:
            await callback.message.answer("⚠️ У этого врача нет доступных дат на ближайшие 2 недели.")
        return

    # Используем новый календарь
    calendar_markup = await SimpleCalendar().start_calendar(
        available_dates=dates,
        days_ahead=14
    )

    try:
        await callback.message.edit_text(
            "📅 Выберите дату приёма:\n\n"
            "📍 - сегодня | 🌴 - выходной\n"
            "Только доступные даты активны",
            reply_markup=calendar_markup
        )
    except Exception:
        await callback.message.answer(
            "📅 Выберите дату приёма:\n\n"
            "📍 - сегодня | 🌴 - выходной\n"
            "Только доступные даты активны",
            reply_markup=calendar_markup
        )

    await state.set_state(BookingStates.date)


# === Обработчик выбора даты из календаря ===
@router.callback_query(BookingStates.date, SimpleCalendarCallback.filter())
async def process_calendar_selection(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    success, selected_date = await SimpleCalendar.process_selection(callback, callback_data)

    if success and selected_date:
        # Пользователь выбрал дату
        date_iso = selected_date.isoformat()

        # Проверяем, доступна ли эта дата для выбранного врача
        data = await state.get_data()
        doctor_id = data.get("doctor_id")

        if not doctor_id:
            await callback.message.answer("❌ Сначала выберите врача.")
            return

        available_dates = get_available_dates_for_doctor(doctor_id)
        if date_iso not in available_dates:
            await callback.answer("❌ Эта дата недоступна для записи", show_alert=True)
            return

        # Продолжаем процесс как в choose_date
        await state.update_data(date=date_iso)
        slots = get_available_slots_for_doctor_on_date(doctor_id, date_iso)

        if not slots:
            try:
                await callback.message.edit_text("⏳ На эту дату нет свободных слотов. Выберите другую дату.")
            except Exception:
                await callback.message.answer("⏳ На эту дату нет свободных слотов. Выберите другую дату.")
            return

        # Создаем сетку кнопок времени
        kb_rows = []
        row = []
        for s in slots:
            sched_id, time_str = s
            row.append(InlineKeyboardButton(text=time_str, callback_data=f"choose_time_{sched_id}"))
            if len(row) == 3:
                kb_rows.append(row)
                row = []
        if row:
            kb_rows.append(row)

        # Кнопки навигации
        kb_rows.append([InlineKeyboardButton(text="🔙 Назад к датам", callback_data="back_to_calendar")])
        kb_rows.append([InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

        try:
            await callback.message.edit_text(f"🕓 Свободные слоты на {date_iso}:", reply_markup=kb)
        except Exception:
            await callback.message.answer(f"🕓 Свободные слоты на {date_iso}:", reply_markup=kb)

        await state.set_state(BookingStates.time)

    elif success and selected_date is None:
        # Пользователь отменил выбор даты
        await callback.message.edit_text("❌ Выбор даты отменен.", reply_markup=main_menu_inline())
        await state.clear()


# === Назад к календарю ===
@router.callback_query(BookingStates.time, F.data == "back_to_calendar")
async def back_to_calendar(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    doctor_id = data.get("doctor_id")
    if not doctor_id:
        await callback.message.answer("❌ Сначала выберите врача.")
        return

    dates = get_available_dates_for_doctor(doctor_id)
    calendar_markup = await SimpleCalendar().start_calendar(
        available_dates=dates,
        days_ahead=14
    )

    try:
        await callback.message.edit_text(
            "📅 Выберите дату приёма:\n\n"
            "📍 - сегодня | 🌴 - выходной\n"
            "Только доступные даты активны",
            reply_markup=calendar_markup
        )
    except Exception:
        await callback.message.answer(
            "📅 Выберите дату приёма:\n\n"
            "📍 - сегодня | 🌴 - выходной\n"
            "Только доступные даты активны",
            reply_markup=calendar_markup
        )

    await state.set_state(BookingStates.date)


# === Назад к выбору врача ===
@router.callback_query(BookingStates.date, F.data == "back_to_doctor")
async def back_to_doctor(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    service_id = data.get("service_id")
    if not service_id:
        # если нет сервиса в памяти — просто вернёмся в меню услуг
        services = get_services()
        items = [(f"{s[1]} — {s[3]}₽", f"choose_service_{s[0]}") for s in services]
        kb = build_list_kb(items, footer_rows=nav_footer())
        try:
            await callback.message.edit_text("🧾 Выберите услугу:", reply_markup=kb)
        except Exception:
            await callback.message.answer("🧾 Выберите услугу:", reply_markup=kb)
        await state.set_state(BookingStates.service)
        return

    doctors = get_doctors_by_service(service_id)
    items = [(f"{d[1]} ({d[2] or 'специальность'})", f"choose_doctor_{d[0]}") for d in doctors]
    kb = build_list_kb(items, footer_rows=nav_footer("back_to_service"))
    try:
        await callback.message.edit_text("👩‍⚕️ Выберите врача:", reply_markup=kb)
    except Exception:
        await callback.message.answer("👩‍⚕️ Выберите врача:", reply_markup=kb)
    await state.set_state(BookingStates.doctor)


# === Выбор времени -> выбор питомца ===
@router.callback_query(BookingStates.time, F.data.startswith("choose_time_"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        schedule_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.message.answer("❌ Неправильный формат времени.")
        return

    await state.update_data(schedule_id=schedule_id)

    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("❗ Пользователь не найден. Введите /start.")
        return

    pets = get_user_pets(user[0])

    if not pets:
        # предложим перейти в раздел "Мои питомцы" (чтобы добавить)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить питомца", callback_data="add_pet")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")]
        ])
        try:
            await callback.message.edit_text(
                "🐾 У вас пока нет питомцев. Чтобы записаться — сначала добавьте питомца.",
                reply_markup=kb
            )
        except Exception:
            await callback.message.answer(
                "🐾 У вас пока нет питомцев. Чтобы записаться — сначала добавьте питомца.",
                reply_markup=kb
            )
        await state.set_state(BookingStates.pet)
        return

    items = [(p[1], f"choose_pet_{p[0]}") for p in pets]
    kb = build_list_kb(items, footer_rows=nav_footer("back_to_time"))

    try:
        await callback.message.edit_text("🐶 Выберите питомца для записи:", reply_markup=kb)
    except Exception:
        await callback.message.answer("🐶 Выберите питомца для записи:", reply_markup=kb)

    await state.set_state(BookingStates.pet)


# === Назад ко времени ===
@router.callback_query(BookingStates.pet, F.data == "back_to_time")
async def back_to_time(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    doctor_id = data.get("doctor_id")
    date_iso = data.get("date")
    if not (doctor_id and date_iso):
        await callback.message.answer("❌ Сначала выберите врача и дату.")
        return

    slots = get_available_slots_for_doctor_on_date(doctor_id, date_iso)
    # строим сетку как в choose_date
    if not slots:
        await callback.message.edit_text("⏳ Нет доступных слотов на выбранную дату.")
        return

    kb_rows = []
    row = []
    for s in slots:
        sched_id, time_str = s
        row.append(InlineKeyboardButton(text=time_str, callback_data=f"choose_time_{sched_id}"))
        if len(row) == 3:
            kb_rows.append(row)
            row = []
    if row:
        kb_rows.append(row)
    kb_rows.append([InlineKeyboardButton(text="🔙 Назад к датам", callback_data="back_to_calendar")])
    kb_rows.append([InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    try:
        await callback.message.edit_text("🕓 Выберите время:", reply_markup=kb)
    except Exception:
        await callback.message.answer("🕓 Выберите время:", reply_markup=kb)

    await state.set_state(BookingStates.time)


# === Выбор питомца -> финализация записи ===
@router.callback_query(BookingStates.pet, F.data.startswith("choose_pet_"))
async def choose_pet(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        pet_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.message.answer("❌ Неправильный формат выбора питомца.")
        return

    await state.update_data(pet_id=pet_id)
    data = await state.get_data()

    schedule_id = data.get("schedule_id")
    user = get_user_by_telegram_id(callback.from_user.id)
    service_id = data.get("service_id")
    date_iso = data.get("date")

    if not (schedule_id and user and service_id and date_iso):
        await callback.message.answer("❌ Ошибка данных. Пожалуйста, начните запись заново.")
        await state.clear()
        return

    try:
        appointment_id = book_slot(schedule_id, user[0], pet_id, service_id)
    except ValueError as e:
        await callback.message.answer(f"⚠️ Невозможно забронировать слот: {e}")
        await state.clear()
        return

    # Получаем информацию для красивого подтверждения
    from db.db_utils import connect
    with connect() as conn:
        cur = conn.cursor()
        # Получаем информацию о питомце
        cur.execute("SELECT name FROM pets WHERE id = ?", (pet_id,))
        pet_name = cur.fetchone()[0]

        # Получаем информацию об услуге
        cur.execute("SELECT name FROM services WHERE id = ?", (service_id,))
        service_name = cur.fetchone()[0]

        # Получаем информацию о враче
        doctor_id = data.get("doctor_id")
        cur.execute("SELECT full_name FROM doctors WHERE id = ?", (doctor_id,))
        doctor_name = cur.fetchone()[0]

        # Получаем время
        cur.execute("SELECT time FROM schedule WHERE id = ?", (schedule_id,))
        time_str = cur.fetchone()[0]

    # подтверждение
    text = (
        f"✅ <b>Запись успешно создана!</b>\n\n"
        f"🐾 <b>Питомец:</b> {pet_name}\n"
        f"👩‍⚕️ <b>Врач:</b> {doctor_name}\n"
        f"🧾 <b>Услуга:</b> {service_name}\n"
        f"📅 <b>Дата и время:</b> {date_iso} в {time_str}\n\n"
        f"<i>Номер записи: #{appointment_id}</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои записи", callback_data="my_appointments")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")]
    ])
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

    await state.clear()