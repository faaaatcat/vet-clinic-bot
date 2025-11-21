# db/db_init.py
import sqlite3
from pathlib import Path
from datetime import date, timedelta
import random

DB_PATH = Path("db/vet_clinic.db")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # === Создание таблиц ===
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        phone TEXT,
        full_name TEXT,
        reg_date TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS pets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        species TEXT,
        age TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        specialty TEXT
    );

    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        duration INTEGER NOT NULL,
        price REAL
    );

    CREATE TABLE IF NOT EXISTS doctor_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER NOT NULL,
        service_id INTEGER NOT NULL,
        FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
        FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
        UNIQUE (doctor_id, service_id)
    );

    CREATE TABLE IF NOT EXISTS schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        is_booked INTEGER DEFAULT 0,
        UNIQUE (doctor_id, date, time),
        FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        pet_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        service_id INTEGER NOT NULL,
        schedule_id INTEGER NOT NULL,
        status TEXT DEFAULT 'scheduled',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        notified_24h INTEGER DEFAULT 0,
        notified_2h INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (pet_id) REFERENCES pets(id),
        FOREIGN KEY (doctor_id) REFERENCES doctors(id),
        FOREIGN KEY (service_id) REFERENCES services(id),
        FOREIGN KEY (schedule_id) REFERENCES schedule(id)
    );
    """)

    # === Добавление тестовых данных ===
    _add_test_data(cur)

    conn.commit()
    conn.close()

    # Генерируем расписание на 14 дней вперед
    generate_schedule_for_all_doctors()
    print("✅ База данных успешно инициализирована с тестовыми данными.")


def _add_test_data(cur):
    """Добавление тестовых данных во все таблицы"""

    # === Врачи ===
    doctors = [
        ("Доктор Иванова Анна", "Терапевт"),
        ("Доктор Петров Сергей", "Хирург"),
        ("Доктор Сидорова Мария", "Стоматолог")
    ]

    for doctor in doctors:
        cur.execute("INSERT OR IGNORE INTO doctors (full_name, specialty) VALUES (?, ?)", doctor)

    # === Услуги ===
    services = [
        ("Первичный осмотр", 30, 1500),
        ("Повторный осмотр", 20, 1000),
        ("Вакцинация", 30, 1200),
        ("Чипирование", 20, 2000),
        ("Стоматологическая чистка", 45, 2500),
        ("Удаление зубного камня", 30, 1800),
        ("Кастрация/стерилизация", 120, 5000),
        ("УЗИ диагностика", 40, 3000),
        ("Рентген", 30, 2200),
        ("Анализы крови", 15, 1500),
        ("Обработка ран", 25, 1200),
        ("Стрижка когтей", 15, 500)
    ]

    for service in services:
        cur.execute("INSERT OR IGNORE INTO services (name, duration, price) VALUES (?, ?, ?)", service)

    # === Связь врачей и услуг ===
    # Терапевт (ID 1) - все основные услуги
    for service_id in [1, 2, 3, 4, 8, 9, 10, 11, 12]:
        cur.execute("INSERT OR IGNORE INTO doctor_services (doctor_id, service_id) VALUES (?, ?)", (1, service_id))

    # Хирург (ID 2) - хирургические услуги
    for service_id in [1, 2, 7, 8, 9, 10, 11]:
        cur.execute("INSERT OR IGNORE INTO doctor_services (doctor_id, service_id) VALUES (?, ?)", (2, service_id))

    # Стоматолог (ID 3) - стоматологические услуги
    for service_id in [1, 2, 5, 6, 8, 9]:
        cur.execute("INSERT OR IGNORE INTO doctor_services (doctor_id, service_id) VALUES (?, ?)", (3, service_id))

    # === Пользователи ===
    users = [
        (100000001, "+79161111111", "Александр Ковалев"),
        (100000002, "+79162222222", "Екатерина Смирнова"),
        (100000003, "+79163333333", "Дмитрий Попov"),
        (100000004, "+79164444444", "Ольга Иванова"),
        (100000005, "+79165555555", "Михаил Петров")
    ]

    for user in users:
        cur.execute(
            "INSERT OR IGNORE INTO users (telegram_id, phone, full_name) VALUES (?, ?, ?)",
            user
        )

    # === Питомцы ===
    pet_names = ["Барсик", "Мурка", "Шарик", "Рекс", "Пушистик"]

    species_list = ["Кот", "Собака", "Грызун", "Птица"]
    age_ranges = ["До 1 года", "1-3 года", "4-7 лет", "8-10 лет", "Старше 10 лет"]

    # Получаем ID пользователей
    cur.execute("SELECT id FROM users ORDER BY id LIMIT 5")
    user_ids = [row[0] for row in cur.fetchall()]

    for i, user_id in enumerate(user_ids):
        if i < len(pet_names):
            species = random.choice(species_list)
            age = random.choice(age_ranges)
            cur.execute(
                "INSERT INTO pets (user_id, name, species, age) VALUES (?, ?, ?, ?)",
                (user_id, pet_names[i], species, age)
            )

    print("✅ Тестовые данные добавлены (без записей на прием)")


def generate_schedule_for_all_doctors(days_ahead=14, work_start=9, work_end=19):
    """
    Генерирует слоты для всех врачей на ближайшие `days_ahead` дней.
    Врачи работают пн-пт, слоты каждый час: от work_start до work_end-1.
    """
    today = date.today()
    end_date = today + timedelta(days=days_ahead)

    with sqlite3.connect(DB_PATH) as conn:
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
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM schedule WHERE date < ?", (cutoff.isoformat(),))
        conn.commit()
