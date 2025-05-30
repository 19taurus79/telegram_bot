import asyncio
import logging # Импортируем модуль логирования
import os
from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from dotenv import load_dotenv

# Импортируем роутеры
from bot.handlers.comands import user_commands
from bot.handlers.text_message import text_messages
from bot.handlers import callback_handlers

# Импортируем наши мидлвари и функции для работы с БД пользователей
from bot.middlewares.auth_middleware import AuthUserMiddleware, create_users_table
from bot.middlewares.logging_middleware import LoggingMiddleware # Импортируем мидлварь логирования

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка базового логирования
logging.basicConfig(
    level=logging.INFO, # Уровень логирования: INFO (можно изменить на DEBUG для более подробных логов)
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__) # Получаем логгер для текущего модуля

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set. Please set it in your .env file.")

async def set_new_commands(bot: Bot):
    """
    Устанавливает или обновляет список команд в меню бота.
    """
    new_commands = [
        BotCommand(command="remains", description="📦 Залишки"),
        BotCommand(command="orders", description="📄 Заявки на товар"),
        BotCommand(command="admin", description="🛠️ Меню адміна"),
        # BotCommand(command="help", description="❓ Получить помощь"),
        # BotCommand(command="settings", description="⚙️ Изменить настройки"),
        # BotCommand(command="about", description="ℹ️ О боте"),
        # Дополнительные команды для администраторов, можно не отображать в меню
        # BotCommand(command="allow_user", description="Разрешить доступ пользователю (админ)"),
        # BotCommand(command="disallow_user", description="Запретить доступ пользователю (админ)"),
        # BotCommand(command="list_users", description="Список пользователей (админ)"),
    ]
    await bot.set_my_commands(new_commands)
    logger.info("Команды бота в меню слева от ввода обновлены.")

async def main():
    # Проверяем и создаем таблицу пользователей в БД (если ее нет)
    # Это должно произойти до запуска поллинга
    await create_users_table()
    logger.info("Проверка и создание таблицы пользователей завершены.")

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    # Регистрация мидлварей на уровне диспетчера
    # Порядок имеет значение:
    # 1. AuthUserMiddleware должна быть первой, чтобы контролировать доступ.
    # 2. LoggingMiddleware может идти после, чтобы логировать только авторизованные действия,
    #    или до, чтобы логировать все попытки. В данном случае логирование всех попыток.
    dp.message.middleware(AuthUserMiddleware())
    dp.callback_query.middleware(AuthUserMiddleware())

    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    # Подключаем роутеры
    dp.include_router(user_commands.router)
    dp.include_router(callback_handlers.router)
    dp.include_router(text_messages.router)

    # Вызываем функцию для установки команд при запуске бота
    await set_new_commands(bot)

    logger.info("Бот запущен и готов к работе!")
    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную (Ctrl+C).")
    except Exception as e:
        logger.exception(f"Произошла фатальная ошибка при запуске бота: {e}")