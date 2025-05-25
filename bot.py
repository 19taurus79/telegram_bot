import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand # Важно импортировать этот класс
from dotenv import load_dotenv
import os
# Импортируем роутеры
from handlers.comands import user_commands
from handlers.text_message import text_messages
from handlers.callbacks import callback_handlers
load_dotenv()
# Если у тебя есть файл config.py
# from config import BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN") # Замени на свой токен!

async def set_new_commands(bot: Bot):
    """
    Устанавливает или обновляет список команд в меню бота.
    """
    new_commands = [
        BotCommand(command="remains", description="📦 Залишки"),
        BotCommand(command="orders", description="📄 Заявки на товар"),
        BotCommand(command="help", description="❓ Получить помощь"),
        BotCommand(command="settings", description="⚙️ Изменить настройки"),
        BotCommand(command="about", description="ℹ️ О боте"),
        # Ты можешь добавить или удалить любые другие команды
        # BotCommand(command="menu", description="Показать главное меню"), # Если нужно вернуть
    ]
    await bot.set_my_commands(new_commands)
    print("Команды бота в меню слева от ввода обновлены.")

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # Подключаем роутеры
    dp.include_router(user_commands.router)
    dp.include_router(callback_handlers.router)
    dp.include_router(text_messages.router)

    # Вызови функцию для установки команд при запуске бота
    await set_new_commands(bot) # <-- Здесь происходит обновление меню

    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())