# db/db_utils.py:
import sqlite3
from pathlib import Path
from datetime import date, timedelta

DB_PATH = Path("db/vet_clinic.db")


def connect():
    """Подключение к базе данных."""
    return sqlite3.connect(DB_PATH)


# =========================
# Doctors / Services
# =========================
def get_doctors():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, full_name, specialty FROM doctors ORDER BY full_name")
        return cur.fetchall()


def add_doctor(full_name, specialty):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO doctors (full_name, specialty) VALUES (?, ?)", (full_name, specialty))
        conn.commit()
        return cur.lastrowid


def get_services():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, duration, price FROM services ORDER BY name")
        return cur.fetchall()


def add_service(name, duration, price):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO services (name, duration, price) VALUES (?, ?, ?)", (name, duration, price))
        conn.commit()
        return cur.lastrowid


# =========================
# Users / Pets
# =========================
def get_user_by_telegram_id(tg_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, telegram_id, phone, full_name FROM users WHERE telegram_id=?", (tg_id,))
        return cur.fetchone()


def get_user_by_phone(phone):
    """Возвращает пользователя по номеру телефона."""
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, telegram_id, phone, full_name FROM users WHERE phone=?", (phone,))
        return cur.fetchone()


def add_user(telegram_id, phone=None, full_name=None):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO users (telegram_id, phone, full_name) VALUES (?, ?, ?)",
            (telegram_id, phone, full_name)
        )
        conn.commit()
        cur.execute("SELECT id FROM users WHERE telegram_id=?", (telegram_id,))
        return cur.fetchone()[0]


def add_pet(user_id, name, species=None, age=None):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO pets (user_id, name, species, age) VALUES (?, ?, ?, ?)",
                    (user_id, name, species, age))
        conn.commit()
        return cur.lastrowid


def get_user_pets(user_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, species, age FROM pets WHERE user_id=? ORDER BY id", (user_id,))
        return cur.fetchall()


# =========================
# Schedule & Booking
# =========================
def generate_schedule_for_all_doctors(days_ahead=14, work_start=9, work_end=19):
    """
    Генерирует слоты для всех врачей на ближайшие `days_ahead` дней.
    Врачи работают пн-пт, слоты каждый час: от work_start до work_end-1.
    """
    today = date.today()
    end_date = today + timedelta(days=days_ahead)
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM doctors")
        doctors = [r[0] for r in cur.fetchall()]
        for doctor_id in doctors:
            current = today
            while current <= end_date:
                if current.weekday() < 5:  # пн-пт
                    iso = current.isoformat()
                    for h in range(work_start, work_end):
                        time_str = f"{h:02d}:00"
                        try:
                            cur.execute(
                                "INSERT OR IGNORE INTO schedule (doctor_id, date, time, is_booked) VALUES (?, ?, ?, 0)",
                                (doctor_id, iso, time_str)
                            )
                        except sqlite3.IntegrityError:
                            pass
                current += timedelta(days=1)
        conn.commit()


def cleanup_old_schedule(keep_days=14):
    """Удаляет старые слоты и оставляет только ближайшие `keep_days` дней."""
    today = date.today()
    cutoff = today - timedelta(days=1)
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM schedule WHERE date < ?", (cutoff.isoformat(),))
        conn.commit()


def get_available_dates_for_doctor(doctor_id, limit_days=14, limit_dates=14):
    today = date.today()
    end_date = today + timedelta(days=limit_days)
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT date
            FROM schedule
            WHERE doctor_id=? AND is_booked=0 AND date BETWEEN ? AND ?
            ORDER BY date
            LIMIT ?
        """, (doctor_id, today.isoformat(), end_date.isoformat(), limit_dates))
        return [r[0] for r in cur.fetchall()]


def get_available_slots_for_doctor_on_date(doctor_id, date_iso):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, time
            FROM schedule
            WHERE doctor_id=? AND date=? AND is_booked=0
            ORDER BY time
        """, (doctor_id, date_iso))
        return cur.fetchall()


def book_slot(schedule_id, user_id, pet_id, service_id):
    """Бронирует слот и создаёт запись в appointments."""
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT doctor_id, date, time, is_booked FROM schedule WHERE id=?", (schedule_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Слот не найден")
        doctor_id, date_iso, time_str, is_booked = row
        if is_booked:
            raise ValueError("Слот уже занят")

        # помечаем слот как забронированный
        cur.execute("UPDATE schedule SET is_booked=1 WHERE id=?", (schedule_id,))

        # создаём appointment
        cur.execute("""
            INSERT INTO appointments (user_id, pet_id, doctor_id, service_id, schedule_id, status)
            VALUES (?, ?, ?, ?, ?, 'scheduled')
        """, (user_id, pet_id, doctor_id, service_id, schedule_id))
        appointment_id = cur.lastrowid
        conn.commit()
        return appointment_id


def get_user_appointments(user_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.id, s.name, d.full_name, sch.date, sch.time, a.status, p.name
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            JOIN doctors d ON a.doctor_id = d.id
            JOIN schedule sch ON a.schedule_id = sch.id
            JOIN pets p ON a.pet_id = p.id
            WHERE a.user_id = ?
            ORDER BY sch.date, sch.time
        """, (user_id,))
        return cur.fetchall()


def cancel_appointment(appointment_id: int, free_slot: bool = False) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        # Сначала получаем schedule_id этой записи
        cur.execute("SELECT schedule_id FROM appointments WHERE id = ?", (appointment_id,))
        result = cur.fetchone()
        if not result:
            return False
        schedule_id = result[0]

        # Удаляем запись
        cur.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))

        # Освобождаем слот, если нужно
        if free_slot:
            cur.execute("UPDATE schedule SET is_booked = 0 WHERE id = ?", (schedule_id,))

        conn.commit()
        return True
    except Exception as e:
        print("Ошибка при отмене записи:", e)
        return False
    finally:
        conn.close()


def get_doctors_by_service(service_id):
    """Возвращает список врачей, которые делают выбранную услугу"""
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT d.id, d.full_name, d.specialty
            FROM doctors d
            JOIN doctor_services ds ON d.id = ds.doctor_id
            WHERE ds.service_id = ?
            ORDER BY d.full_name
        """, (service_id,))
        return cur.fetchall()