from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from datetime import datetime, timedelta, date
from typing import Optional, Tuple


class SimpleCalendarCallback(CallbackData, prefix="simple_cal"):
    action: str  # "select", "ignore"
    date_iso: str  # YYYY-MM-DD


class SimpleCalendar:

    @staticmethod
    async def start_calendar(available_dates: list, days_ahead: int = 7) -> InlineKeyboardMarkup:
        """
        Создает календарь на ближайшие days_ahead дней с учетом доступных дат
        """
        today = date.today()
        markup = []

        # Заголовок
        markup.append([
            InlineKeyboardButton(
                text="📅 Выберите дату",
                callback_data=SimpleCalendarCallback(
                    action="ignore",
                    date_iso="header"
                ).pack()
            )
        ])

        # Создаем правильный порядок дней недели для отображаемого периода
        week_days_header = []
        current_header_date = today

        for i in range(days_ahead):
            day_index = current_header_date.weekday()
            day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            week_days_header.append(day_names[day_index])
            current_header_date += timedelta(days=1)

        # Заголовок дней недели
        markup.append([
            InlineKeyboardButton(
                text=day,
                callback_data=SimpleCalendarCallback(action="ignore", date_iso=f"wd_{i}").pack()
            ) for i, day in enumerate(week_days_header)
        ])

        # Генерируем кнопки с датами
        current_date = today
        date_buttons = []

        for i in range(days_ahead):
            day_number = current_date.day
            date_iso = current_date.isoformat()

            # Форматируем текст кнопки
            if current_date == today:
                button_text = f"📍{day_number}"
            elif current_date.weekday() >= 5:  # Суббота и воскресенье
                button_text = f"🌴{day_number}"
            else:
                button_text = f"{day_number}"

            # Проверяем доступность даты
            if date_iso in available_dates:
                date_buttons.append(
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=SimpleCalendarCallback(
                            action="select",
                            date_iso=date_iso
                        ).pack()
                    )
                )
            else:
                date_buttons.append(
                    InlineKeyboardButton(
                        text="·",
                        callback_data=SimpleCalendarCallback(action="ignore", date_iso="unavailable").pack()
                    )
                )

            current_date += timedelta(days=1)

        # Разбиваем на строки (можно настроить количество кнопок в строке)
        buttons_per_row = 7  # Все дни в одной строке
        for i in range(0, len(date_buttons), buttons_per_row):
            markup.append(date_buttons[i:i + buttons_per_row])

        # Подпись с диапазоном дат
        end_date = today + timedelta(days=days_ahead - 1)
        date_range = f"{today.strftime('%d.%m')}-{end_date.strftime('%d.%m')}"
        markup.append([
            InlineKeyboardButton(
                text=f"📆 {date_range}",
                callback_data=SimpleCalendarCallback(action="ignore", date_iso="range").pack()
            )
        ])


        # Кнопки навигации
        markup.append([
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=SimpleCalendarCallback(action="ignore", date_iso="cancel").pack()
            )
        ])

        return InlineKeyboardMarkup(inline_keyboard=markup)

    @staticmethod
    async def process_selection(query: CallbackQuery, data: SimpleCalendarCallback) -> Tuple[bool, Optional[date]]:
        """
        Обрабатывает выбор даты
        Возвращает: (success, selected_date)
        """
        if data.action == "ignore":
            if data.date_iso == "cancel":
                await query.message.edit_text("❌ Выбор даты отменен")
                return True, None
            await query.answer()
            return False, None

        if data.action == "select":
            try:
                selected_date = datetime.strptime(data.date_iso, "%Y-%m-%d").date()
                await query.answer(f"✅ Выбрана дата: {selected_date.strftime('%d.%m.%Y')}")
                return True, selected_date
            except ValueError:
                await query.answer("❌ Ошибка выбора даты")
                return False, None

        return False, None


# Альтернативная версия календаря, которая всегда показывает полные недели
class WeekCalendar:

    @staticmethod
    async def start_calendar(available_dates: list, weeks_ahead: int = 1) -> InlineKeyboardMarkup:
        """
        Создает календарь на полные недели
        """
        today = date.today()
        markup = []

        # Заголовок
        markup.append([
            InlineKeyboardButton(
                text="📅 Выберите дату",
                callback_data=SimpleCalendarCallback(action="ignore", date_iso="header").pack()
            )
        ])

        # Стандартные дни недели
        week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        markup.append([
            InlineKeyboardButton(text=day,
                                 callback_data=SimpleCalendarCallback(action="ignore", date_iso=f"wd_{i}").pack())
            for i, day in enumerate(week_days)
        ])

        # Находим понедельник текущей недели
        days_since_monday = today.weekday()
        start_date = today - timedelta(days=days_since_monday)

        # Генерируем недели
        current_date = start_date
        total_days = weeks_ahead * 7

        for week in range(weeks_ahead):
            week_row = []
            for day in range(7):
                date_iso = current_date.isoformat()
                day_number = current_date.day

                # Форматируем текст кнопки
                if current_date == today:
                    button_text = f"📍{day_number}"
                elif current_date.weekday() >= 5:
                    button_text = f"🌴{day_number}"
                else:
                    button_text = f"{day_number}"

                # Проверяем доступность (только будущие даты)
                is_available = date_iso in available_dates and current_date >= today

                if is_available:
                    week_row.append(
                        InlineKeyboardButton(
                            text=button_text,
                            callback_data=SimpleCalendarCallback(action="select", date_iso=date_iso).pack()
                        )
                    )
                else:
                    week_row.append(
                        InlineKeyboardButton(
                            text="·",
                            callback_data=SimpleCalendarCallback(action="ignore", date_iso="unavailable").pack()
                        )
                    )

                current_date += timedelta(days=1)

            markup.append(week_row)

        # Подпись с диапазоном дат
        end_date = start_date + timedelta(days=total_days - 1)
        date_range = f"{start_date.strftime('%d.%m')}-{end_date.strftime('%d.%m')}"
        markup.append([
            InlineKeyboardButton(
                text=f"📆 {date_range}",
                callback_data=SimpleCalendarCallback(action="ignore", date_iso="range").pack()
            )
        ])

        # Кнопки навигации
        markup.append([
            InlineKeyboardButton(text="❌ Отмена",
                                 callback_data=SimpleCalendarCallback(action="ignore", date_iso="cancel").pack())
        ])

        return InlineKeyboardMarkup(inline_keyboard=markup)