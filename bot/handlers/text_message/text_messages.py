from aiogram import Router, types
from aiogram.enums import ParseMode

# Создаем роутер для хендлеров
router = Router()

@router.message()
async def echo_message(message: types.Message):
    if message.text:
        # Пример использования Markdown
        await message.answer(f"Ты сказал: *{message.text}*", parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await message.answer("Я получил сообщение, но оно не содержит текста.")