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
        ("Иванова Анна Александровна", "Терапевт"),
        ("Петров Сергей Иванович", "Хирург"),
        ("Сидорова Мария Петровна", "Стоматолог")
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
        (100000001, "79161111111", "Александр Ковалев"),
        (100000002, "79162222222", "Екатерина Смирнова"),
        (100000003, "79163333333", "Дмитрий Попов"),
        (100000004, "79164444444", "Ольга Иванова"),
        (100000005, "79165555555", "Михаил Петров"),
        (100000006, "+79166666666", "Анна Сидорова"),
        (100000007, "+79167777777", "Сергей Кузнецов"),
        (100000008, "+79168888888", "Мария Новикова"),
        (100000009, "+79169999999", "Алексей Морозов"),
        (100000010, "+79161010101", "Наталья Зайцева"),
        (100000011, "+79161111112", "Иван Соколов"),
        (100000012, "+79161111113", "Татьяна Павлова"),
        (100000013, "+79161111114", "Владимир Лебедев"),
        (100000014, "+79161111115", "Елена Козлова"),
        (100000015, "+79161111116", "Павел Егоров"),
        (100000016, "+79161111117", "Юлия Орлова"),
        (100000017, "+79161111118", "Андрей Алексеев"),
        (100000018, "+79161111119", "Ирина Макарова"),
        (100000019, "+79161111120", "Роман Федоров"),
        (100000020, "+79161111121", "Светлана Васнецова"),
        (100000021, "+79161111122", "Артем Дмитриев"),
        (100000022, "+79161111123", "Алина Жукова"),
        (100000023, "+79161111124", "Константин Белов"),
        (100000024, "+79161111125", "Людмила Комарова"),
        (100000025, "+79161111126", "Григорий Тихонов"),
        (100000026, "+79161111127", "Валентина Романова"),
        (100000027, "+79161111128", "Станислав Филиппов"),
        (100000028, "+79161111129", "Ксения Маркова"),
        (100000029, "+79161111130", "Виктор Воронов"),
        (100000030, "+79161111131", "Оксана Полякова")
    ]

    for user in users:
        cur.execute(
            "INSERT OR IGNORE INTO users (telegram_id, phone, full_name) VALUES (?, ?, ?)",
            user
        )

    # === Питомцы ===
    pet_names = [
        "Барсик", "Мурка", "Шарик", "Рекс", "Пушистик", "Симба", "Зефирка", "Боня",
        "Кексик", "Люси", "Чарли", "Марсик", "Герда", "Тигра", "Оскар", "Багира",
        "Цезарь", "Джесси", "Рыжик", "Снежок", "Альма", "Вольт", "Грейси", "Луна",
        "Спарки", "Филя", "Хлоя", "Яша", "Зоя", "Ирис"
    ]

    species_list = ["Кот", "Собака", "Грызун", "Птица"]
    age_ranges = ["До 1 года", "1-3 года", "4-7 лет", "8-10 лет", "Старше 10 лет"]

    # Получаем ID пользователей
    cur.execute("SELECT id FROM users ORDER BY id")
    user_ids = [row[0] for row in cur.fetchall()]

    for i, user_id in enumerate(user_ids):
        if i < len(pet_names):
            species = random.choice(species_list)
            age = random.choice(age_ranges)
            cur.execute(
                "INSERT INTO pets (user_id, name, species, age) VALUES (?, ?, ?, ?)",
                (user_id, pet_names[i], species, age)
            )

    # === Тестовые записи на прием ===
    # Создаем несколько записей для демонстрации
    # Для этого сначала нужно сгенерировать расписание
    conn_temp = sqlite3.connect(DB_PATH)
    cur_temp = conn_temp.cursor()

    # Получаем доступные слоты
    cur_temp.execute("""
        SELECT s.id, s.doctor_id, s.date, s.time 
        FROM schedule s 
        WHERE s.is_booked = 0 
        ORDER BY s.date, s.time 
        LIMIT 10
    """)
    available_slots = cur_temp.fetchall()

    # Получаем пользователей и их питомцев
    cur_temp.execute("""
        SELECT u.id, p.id 
        FROM users u 
        JOIN pets p ON u.id = p.user_id 
        LIMIT 5
    """)
    user_pets = cur_temp.fetchall()

    # Создаем тестовые записи
    for i, (user_id, pet_id) in enumerate(user_pets):
        if i < len(available_slots):
            slot_id, doctor_id, slot_date, slot_time = available_slots[i]

            # Выбираем случайную услугу, которую предоставляет этот врач
            cur_temp.execute("""
                SELECT service_id FROM doctor_services 
                WHERE doctor_id = ? 
                LIMIT 1
            """, (doctor_id,))
            service_result = cur_temp.fetchone()

            if service_result:
                service_id = service_result[0]

                # Бронируем слот
                cur_temp.execute("UPDATE schedule SET is_booked = 1 WHERE id = ?", (slot_id,))

                # Создаем запись
                cur_temp.execute("""
                    INSERT INTO appointments 
                    (user_id, pet_id, doctor_id, service_id, schedule_id, status) 
                    VALUES (?, ?, ?, ?, ?, 'scheduled')
                """, (user_id, pet_id, doctor_id, service_id, slot_id))

    conn_temp.commit()
    conn_temp.close()


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
