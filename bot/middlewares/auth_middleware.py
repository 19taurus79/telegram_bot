from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, List
import logging
import os
import asyncpg

# Путь к вашей базе данных пользователей Telegram (PostgreSQL connection string)
USERS_DB_URL = os.getenv("TELEGRAM_USERS_DB_URL")

# Настройка логирования для этой мидлвари
logger = logging.getLogger(__name__)


# Асинхронная функция для создания таблицы пользователей (если ее нет)
async def create_users_table():
    if not USERS_DB_URL:
        logger.error(
            "TELEGRAM_USERS_DB_URL не установлен в переменных окружения. Таблица пользователей не будет создана.")
        return

    conn = None
    try:
        conn = await asyncpg.connect(USERS_DB_URL)
        # Добавляем поле phone_number TEXT DEFAULT NULL
        await conn.execute("""
                           CREATE TABLE IF NOT EXISTS users
                           (
                               telegram_id        BIGINT PRIMARY KEY,
                               username           TEXT,
                               first_name         TEXT,
                               last_name          TEXT,
                               phone_number       TEXT                     DEFAULT NULL, -- <-- НОВОЕ ПОЛЕ
                               is_allowed         BOOLEAN                  DEFAULT FALSE,
                               registration_date  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                               last_activity_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                           );
                           """)
        logger.info(
            f"Таблица 'users' в PostgreSQL ({USERS_DB_URL.split('@')[-1]}) успешно создана или уже существует.")
    except Exception as e:
        logger.error(
            f"Ошибка при создании таблицы пользователей в PostgreSQL: {e}")
    finally:
        if conn:
            await conn.close()


# Асинхронная функция для сохранения или обновления информации о пользователе
# Phone_number не передается в этой функции, так как будет управляться вручную
async def save_or_update_user_info(telegram_id: int, username: str,
                                   first_name: str, last_name: str):
    if not USERS_DB_URL:
        logger.error(
            "TELEGRAM_USERS_DB_URL не установлен. Информация о пользователе не будет сохранена.")
        return

    conn = None
    try:
        conn = await asyncpg.connect(USERS_DB_URL)

        # Обновляем запрос INSERT ... ON CONFLICT
        # Обратите внимание, phone_number здесь не упоминается
        await conn.execute("""
                           INSERT INTO users (telegram_id, username, first_name, last_name, last_activity_date)
                           VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                           ON CONFLICT (telegram_id) DO UPDATE
                               SET username           = $2,
                                   first_name         = $3,
                                   last_name          = $4,
                                   last_activity_date = CURRENT_TIMESTAMP;
                           """, telegram_id, username, first_name, last_name)

        logger.debug(
            f"Информация о пользователе {telegram_id} сохранена/обновлена.")
    except Exception as e:
        logger.error(
            f"Ошибка при сохранении/обновлении информации о пользователе {telegram_id} в PostgreSQL: {e}")
    finally:
        if conn:
            await conn.close()


# Асинхронная функция для проверки, разрешен ли доступ пользователю
async def is_user_allowed(telegram_id: int) -> bool:
    if not USERS_DB_URL:
        logger.error(
            "TELEGRAM_USERS_DB_URL не установлен. Проверка доступа невозможна.")
        return False

    conn = None
    try:
        conn = await asyncpg.connect(USERS_DB_URL)
        result = await conn.fetchval(
            "SELECT is_allowed FROM users WHERE telegram_id = $1;", telegram_id)
        if result is None:
            return False
        return result
    except Exception as e:
        logger.error(
            f"Ошибка при проверке статуса разрешения для пользователя {telegram_id} в PostgreSQL: {e}")
        return False
    finally:
        if conn:
            await conn.close()


# Асинхронная функция для установки статуса разрешения (для администратора)
async def set_user_allowed_status(telegram_id: int, status: bool) -> bool:
    if not USERS_DB_URL:
        logger.error(
            "TELEGRAM_USERS_DB_URL не установлен. Изменение статуса доступа невозможно.")
        return False

    conn = None
    try:
        conn = await asyncpg.connect(USERS_DB_URL)
        result = await conn.execute(
            "UPDATE users SET is_allowed = $1 WHERE telegram_id = $2;", status,
            telegram_id)
        if result == "UPDATE 1":
            logger.info(
                f"Статус доступа для пользователя {telegram_id} установлен на {status}")
            return True
        logger.warning(
            f"Пользователь {telegram_id} не найден для изменения статуса.")
        return False
    finally:
        if conn:
            await conn.close()


# Асинхронная функция для получения информации о пользователе по ID
async def get_user_info(telegram_id: int) -> Dict[str, Any] | None:
    if not USERS_DB_URL:
        logger.error(
            "TELEGRAM_USERS_DB_URL не установлен. Информация о пользователе не может быть получена.")
        return None

    conn = None
    try:
        conn = await asyncpg.connect(USERS_DB_URL)
        # Добавляем phone_number в SELECT
        row = await conn.fetchrow(
            "SELECT telegram_id, username, first_name, last_name, phone_number, is_allowed, registration_date, last_activity_date FROM users WHERE telegram_id = $1;",
            telegram_id)
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(
            f"Ошибка при получении информации о пользователе {telegram_id}: {e}")
        return None
    finally:
        if conn:
            await conn.close()


# Асинхронная функция для получения списка всех пользователей
async def get_all_users() -> List[Dict[str, Any]]:
    if not USERS_DB_URL:
        logger.error(
            "TELEGRAM_USERS_DB_URL не установлен. Список пользователей не может быть получен.")
        return []

    conn = None
    try:
        conn = await asyncpg.connect(USERS_DB_URL)
        # Добавляем phone_number в SELECT
        rows = await conn.fetch(
            "SELECT telegram_id, username, first_name, last_name, phone_number, is_allowed, registration_date, last_activity_date FROM users ORDER BY registration_date DESC;")
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Ошибка при получении списка всех пользователей: {e}")
        return []
    finally:
        if conn:
            await conn.close()


# НОВАЯ ФУНКЦИЯ (или ОБНОВЛЕННАЯ): Для обновления только номера телефона
# Эта функция будет вызываться вами вручную, или через админ-интерфейс,
# а не автоматически ботом
async def update_user_phone_number(telegram_id: int,
                                   phone_number: str | None) -> bool:
    if not USERS_DB_URL:
        logger.error(
            "TELEGRAM_USERS_DB_URL не установлен. Обновление номера телефона невозможно.")
        return False

    conn = None
    try:
        conn = await asyncpg.connect(USERS_DB_URL)
        # Если phone_number None, то это значит, что мы хотим установить его в NULL
        # Если phone_number пустая строка, то это тоже может быть NULL
        sql_phone_number = phone_number if phone_number else None

        result = await conn.execute(
            "UPDATE users SET phone_number = $1 WHERE telegram_id = $2;",
            sql_phone_number, telegram_id)

        if result == "UPDATE 1":
            logger.info(
                f"Номер телефона для пользователя {telegram_id} обновлен до {phone_number}.")
            return True
        logger.warning(
            f"Пользователь {telegram_id} не найден для обновления номера телефона.")
        return False
    except Exception as e:
        logger.error(
            f"Ошибка при обновлении номера телефона для пользователя {telegram_id} в PostgreSQL: {e}")
        return False
    finally:
        if conn:
            await conn.close()


# Класс мидлвари для авторизации и сохранения данных пользователя
class AuthUserMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Any],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        user_id = user.id

        # Вызываем save_or_update_user_info без параметра phone_number
        await save_or_update_user_info(
            user_id,
            user.username,
            user.first_name if user.first_name else '',
            user.last_name if user.last_name else ''
        )

        if await is_user_allowed(user_id):
            return await handler(event, data)
        else:
            if isinstance(event, Message):
                await event.answer(
                    "У вас нет доступа к этому боту. Пожалуйста, свяжитесь с администратором.")
            elif isinstance(event, CallbackQuery):
                await event.message.answer(
                    "У вас нет доступа к этому боту. Пожалуйста, свяжитесь с администратором.")
                await event.answer("Доступ запрещен.")
            logger.warning(
                f"Неавторизованная попытка доступа от пользователя: {user_id} ({user.full_name})")
            return