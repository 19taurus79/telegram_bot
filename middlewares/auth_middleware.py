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
                               phone_number       TEXT                     DEFAULT NULL,
                               is_allowed         BOOLEAN                  DEFAULT FALSE,
                               is_admin           BOOLEAN                  DEFAULT FALSE,
                               is_guest           BOOLEAN                  DEFAULT FALSE,
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
                           INSERT INTO users (telegram_id, username, first_name, last_name, last_activity_date, is_allowed, is_admin, is_guest)
                           VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP, FALSE, FALSE, FALSE)
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
        # Добавляем все поля в SELECT
        row = await conn.fetchrow(
            "SELECT telegram_id, username, first_name, last_name, phone_number, is_allowed, is_admin, is_guest, registration_date, last_activity_date FROM users WHERE telegram_id = $1;",
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
        # Добавляем все поля в SELECT
        rows = await conn.fetch(
            "SELECT telegram_id, username, first_name, last_name, phone_number, is_allowed, is_admin, is_guest, registration_date, last_activity_date FROM users ORDER BY registration_date DESC;")
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

        # Проверяем не является ли сообщение процессом регистрации
        is_registration = False
        text = getattr(event, 'text', '') or ''
        # Разрешаем команды старт, ввод ФИО, запросы доступа (кнопки)
        if hasattr(event, "data") and event.data:
            if event.data in ["request_access"] or event.data.startswith("approve_") or event.data.startswith("reject_"):
                is_registration = True
        elif text.startswith("/start") or text.isdigit():
            # Это может быть 4-значный код или команда /start
            is_registration = True
        
        # Получаем данные пользователя для проверки (чтобы не перезаписывать is_allowed на False для существующих пользователей не-registration логикой выше)
        # В функции get_user_info можем проверить существует ли
        existing_user = await get_user_info(user_id)
        if not existing_user:
            await save_or_update_user_info(
                user_id,
                user.username,
                user.first_name if user.first_name else '',
                user.last_name if user.last_name else ''
            )

        # Если пользователь администратор, то к нему вообще нет ограничений
        # или если state = RegistrationStates (мы это не проверяем здесь напрямую, полагаемся на is_registration)

        is_allowed = await is_user_allowed(user_id)
        
        # Если статус allowed=True ИЛИ это запрос регистрации - пропускаем к хендлерм
        if is_allowed or is_registration:
            # Обновляем активность только для дозволенных запросов
            if is_allowed:
                 await save_or_update_user_info(
                    user_id,
                    user.username,
                    user.first_name if user.first_name else '',
                    user.last_name if user.last_name else ''
                )
            return await handler(event, data)
        else:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📨 Надіслати запит", callback_data="request_access")]
            ])
            if isinstance(event, Message):
                await event.answer(
                    "🤖 Вас немає в системі або очікується підтвердження. Будь ласка, зверніться до розробника для отримання доступу.",
                    reply_markup=keyboard
                )
            elif isinstance(event, CallbackQuery):
                await event.message.answer(
                    "🤖 Вас немає в системі або очікується підтвердження.",
                    reply_markup=keyboard
                )
                await event.answer("Доступ заборонено.", show_alert=True)
            logger.warning(
                f"Неавторизованная попытка доступа от пользователя: {user_id} ({user.full_name})")
            return