from aiogram import Router, types
from aiogram.types import CallbackQuery

# Создаем роутер для хендлеров callback-запросов
router = Router()

@router.callback_query(lambda c: c.data == "show_my_data")
async def process_show_my_data_callback(callback_query: CallbackQuery):
    user = callback_query.from_user
    await callback_query.message.edit_text(
        f"Вот твои данные:\n"
        f"ID: `{user.id}`\n"
        f"Имя: `{user.full_name}`\n"
        f"Юзернейм: `@{user.username if user.username else 'Нет'}`",
        parse_mode="Markdown"
    )
    # Обязательно ответь на callback_query, иначе кнопка будет выглядеть "зависшей"
    await callback_query.answer("Данные показаны!", show_alert=False) # show_alert=True покажет всплывающее окно

@router.callback_query(lambda c: c.data == "about_bot")
async def process_about_bot_callback(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "Я демонстрационный Telegram-бот, созданный с помощью aiogram 3. "
        "Я умею отвечать на команды, обрабатывать текст и показывать инлайн-клавиатуры."
    )
    await callback_query.answer("Информация о боте.")

@router.callback_query(lambda c: c.data == "help_info")
async def process_help_info_callback(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "Если тебе нужна помощь, ты можешь задать свой вопрос напрямую "
        "или ознакомиться с разделом FAQ на нашем сайте."
    )
    await callback_query.answer("Помощь.")

# Общий хендлер для всех остальных callback-запросов (если нужно)
@router.callback_query()
async def process_any_callback(callback_query: CallbackQuery):
    await callback_query.answer(f"Ты нажал на кнопку с данными: {callback_query.data}")