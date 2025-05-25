from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.db.get_products import get_products, get_product_by_id
from utils.db.get_remains import get_remains
from utils.db.get_submissions import get_submissions

# Создаем роутер для хендлеров
router = Router()
class BotStates(StatesGroup):
    waiting_for_nomenclature = State()
    waiting_for_product_selection = State() # Новое состояние для ожидания выбора продукта
    waiting_for_submissions_nomenclature = State()  # Новое состояние для заявок
    waiting_for_submissions_product_selection = State()  # Новое состояние для выбора продукта в заявках
@router.message(CommandStart())
async def cmd_start(message: types.Message):
    # Создаем инлайн-клавиатуру для меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Показать мои данные", callback_data="show_my_data")],
        [InlineKeyboardButton(text="О боте", callback_data="about_bot")],
        [InlineKeyboardButton(text="Помощь", callback_data="help_info")],
        [InlineKeyboardButton(text="Посетить наш сайт", url="https://www.example.com")] # Пример кнопки-ссылки
    ])

    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n\n"
        "Я могу многое! Выбери одну из опций ниже:",
        reply_markup=keyboard
    )

@router.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext):
    # Можно использовать тот же код, что и для /start, чтобы повторно вывести меню
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Показать мои данные", callback_data="show_my_data")],
        [InlineKeyboardButton(text="О боте", callback_data="about_bot")],
        [InlineKeyboardButton(text="Помощь", callback_data="help_info")],
        [InlineKeyboardButton(text="Посетить наш сайт", url="https://www.example.com")]
    ])
    await message.answer("Вот что я могу предложить:", reply_markup=keyboard)

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Я могу помочь тебе с этим и тем. Попробуй отправить мне сообщение или выбери опцию из меню!")

@router.message(Command("remains"))
async def cmd_remains_start(message: types.Message, state: FSMContext):
    """
    Обрабатывает команду /remains. Всегда запрашивает номенклатуру у пользователя.
    """
    await message.delete()
    await message.answer("Пожалуйста, укажите номенклатуру (или часть названия), которую вы хотите найти:")
    await state.set_state(BotStates.waiting_for_nomenclature)


@router.message(BotStates.waiting_for_nomenclature)
async def process_nomenclature_query(message: types.Message, state: FSMContext):
    """
    Обрабатывает текстовый ввод после запроса номенклатуры, находит совпадения
    и предлагает их в инлайн-клавиатуре.
    """
    query = message.text.strip()
    if not query:
        await message.answer("Вы ничего не ввели. Пожалуйста, укажите номенклатуру.")
        return

    await message.answer(f"Ищу продукты, содержащие: <b>{query}</b>...", parse_mode=ParseMode.HTML)

    try:
        # await DB.start_connection()

        # Ищем ProductGuide, чьё строковое представление (product) содержит нашу номенклатуру
        # Используем .lower() для регистронезависимого поиска
        # Используем .contains() для поиска подстроки
        # product_entries = await ProductGuide.objects().where(
        #     ProductGuide.product.ilike(f"%{query.lower()}%")
        # ).limit(10).all() # Ограничим количество результатов, чтобы клавиатура не была слишком большой
        product_entries = await get_products(query)

        if not product_entries:

            await message.answer(f"Не удалось найти продукты с номенклатурой, содержащей: <b>{query}</b>.", parse_mode=ParseMode.HTML)
            await state.clear()
            return

        # Создаем инлайн-клавиатуру
        builder = InlineKeyboardBuilder()
        for product_entry in product_entries:
            # `product_entry.id` - это UUID, который мы будем передавать через callback_data
            # `product_entry.product.capitalize()` - это название, которое увидит пользователь
            builder.button(
                text=product_entry['product'],
                callback_data=f"select_product_remains:{product_entry['id']}"
            )
        builder.adjust(1) # Кнопки будут в один столбец

        await message.answer(
            "Найдено несколько совпадений. Пожалуйста, выберите нужный продукт:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(BotStates.waiting_for_product_selection) # Переходим в новое состояние
        await state.update_data(product_query=query) # Сохраняем исходный запрос, если понадобится

    except Exception as e:
        print(f"Ошибка при поиске продуктов: {e}")

        await message.answer(f"Произошла ошибка при поиске продуктов. Попробуйте еще раз. Ошибка: `{e}`", parse_mode=ParseMode.HTML)
        await state.clear()
    # finally:
        # await DB.close_connection()


@router.callback_query(lambda c: c.data and c.data.startswith('select_product_remains:'))
async def process_product_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор продукта из инлайн-клавиатуры.
    """
    await callback_query.answer() # Убираем "часики" с кнопки
    product_uuid = callback_query.data.split(':')[1] # Извлекаем UUID продукта

    # await callback_query.message.edit_text("Выбрано. Ищу остатки...") # Изменяем сообщение бота

    try:
        # await DB.start_connection()

        # Ищем продукт по UUID
        product_entry = await get_product_by_id(product_uuid)
        if not product_entry:
            await callback_query.message.answer("Продукт не найден в справочнике.")
            return

        # Получаем все остатки для данного продукта
        remains_for_product = await get_remains(product_entry[0]['id'])

        response_parts = []
        if remains_for_product:
            response_parts.append(f"📦 <b><u>*Остатки для продукта: {product_entry[0]['product']}*</u></b>\n")
            for r in remains_for_product:
                if r['line_of_business'] in ['Власне виробництво насіння','Насіння']:
                    response_parts.append(
                        f"  - Партія: {r['nomenclature_series']}\n"
                        f"  - МТН: {r['mtn']}\n"
                        f"  - Страна походження: {r['origin_country']}\n"
                        f"  - Схожість: {r['germination']}\n"
                        f"  - Рік урожаю: {r['crop_year']}\n"
                        f"  - Вага: {r['weight']}\n"
                        f"  - Наявність (Бух.): {r['buh']}\n"
                        f"  - Наявність (Склад): {r['skl']}\n"

                    )
                else:
                    response_parts.append(
                        f"  - Партія: {r['nomenclature_series']}\n"
                        f"  - Наявність (Бух.): {r['buh']}\n"
                        f"  - Наявність (Склад): {r['skl']}\n"
                    )
        else:
            response_parts.append(f"📦 *Продукт: {product_entry[0]['product']}*")
            response_parts.append("  _Остатков не найдено._")

        final_response = "\n".join(response_parts)
        if len(final_response) > 4000:
            await callback_query.message.answer("Найдено слишком много результатов. Пожалуйста, уточните запрос.")
        else:

            await callback_query.message.answer(final_response, parse_mode=ParseMode.HTML)

    except Exception as e:
        print(f"Ошибка при поиске остатков по выбранному продукту: {e}")

        await callback_query.message.answer(f"Произошла ошибка при поиске остатков. Попробуйте еще раз. Ошибка: `{e}`", parse_mode=ParseMode.HTML)
    # finally:
    #     # await DB.close_connection()
    #     await state.clear() # Очищаем состояние после обработки



@router.message(Command("orders"))
async def cmd_submissions_start(message: types.Message, state: FSMContext):
    """
    Обрабатывает команду /submissions. Запрашивает номенклатуру у пользователя.
    """
    await message.delete()
    await message.answer("Пожалуйста, укажите номенклатуру (или часть названия) товара, по которому нужно найти заявки:", parse_mode=ParseMode.HTML)
    await state.set_state(BotStates.waiting_for_submissions_nomenclature)


@router.message(BotStates.waiting_for_submissions_nomenclature)
async def process_submissions_nomenclature_query(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод номенклатуры для заявок, ищет совпадения и предлагает выбор.
    """
    query = message.text.strip()
    if not query:
        await message.answer("Вы ничего не ввели. Пожалуйста, укажите номенклатуру.", parse_mode=ParseMode.HTML)
        return

    try:
        await message.delete() # Удаляем сообщение пользователя
    except Exception as e:
        print(f"Не удалось удалить сообщение пользователя: {e}")

    await message.answer(f"Ищу продукты, содержащие: <b>{query}</b>...", parse_mode=ParseMode.HTML)

    try:


        product_entries = await get_products(query)

        if not product_entries:
            await message.answer(f"Не удалось найти продукты с номенклатурой, содержащей: <b>{query}</b>.", parse_mode=ParseMode.HTML)
            await state.clear()
            return

        builder = InlineKeyboardBuilder()
        for product_entry in product_entries:
            button_text = product_entry['product']
            builder.button(
                text=button_text,
                callback_data=f"select_product_submissions:{product_entry['id']}" # callback_data для заявок
            )
        builder.adjust(1)

        await message.answer(
            "Найдено несколько совпадений. Пожалуйста, выберите нужный продукт:",
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.HTML
        )
        await state.set_state(BotStates.waiting_for_submissions_product_selection) # Переходим в новое состояние
        await state.update_data(product_query=query)

    except Exception as e:
        print(f"Ошибка при поиске продуктов для заявок: {e}")
        await message.answer(f"Произошла ошибка при поиске продуктов. Попробуйте еще раз. Ошибка: <code>{e}</code>", parse_mode=ParseMode.HTML)
        await state.clear()



@router.callback_query(lambda c: c.data and c.data.startswith('select_product_submissions:'))
async def process_submissions_product_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор продукта из инлайн-клавиатуры для заявок.
    """
    await callback_query.answer()
    product_uuid = callback_query.data.split(':')[1]

    # try:
    #     if callback_query.message:
    #         await callback_query.message.edit_text("Выбрано. Ищу заявки...")
    # except Exception as e:
    #     print(f"Не удалось отредактировать сообщение: {e}")
    #     await callback_query.message.answer("Выбрано. Ищу заявки...", parse_mode=ParseMode.HTML)

    try:


        product_entry = await get_product_by_id(product_uuid)
        if not product_entry:
            await callback_query.message.answer("Продукт не найден в справочнике.", parse_mode=ParseMode.HTML)
            return

        # Ищем заявки, связанные с этим product_id
        submissions_data = await get_submissions(product_entry[0]['id'])

        response_parts = []
        if submissions_data:

            response_parts.append(f"📄 <b>Заявки для продукта: {product_entry[0]['product']}</b>\n")

            for s in submissions_data:
                response_parts.append(
                    f"  - Контрагент: {s['client']}\n"
                    f"  - Менеджер: {s['manager']}\n"
                    f"  - Доповнення: {s['contract_supplement']}\n"
                    f"  - Кількість: {s['different']}\n"
                )


        else:

            response_parts.append(f"📄 <b>Продукт: {product_entry[0]['product']}</b>\n")
            response_parts.append("  <i>Заявок не найдено.</i>\n")

        final_response = "\n".join(response_parts)

        if len(final_response) > 4000:
            await callback_query.message.answer("Найдено слишком много результатов. Пожалуйста, уточните запрос.", parse_mode=ParseMode.HTML)
        else:
            try:
                await callback_query.message.answer(final_response, parse_mode=ParseMode.HTML)
            except Exception as e:
                print(f"Не удалось отредактировать финальное сообщение: {e}")
                await callback_query.message.answer(final_response, parse_mode=ParseMode.HTML)

    except Exception as e:
        print(f"Ошибка при поиске заявок по выбранному продукту: {e}")
        error_message = f"Произошла ошибка при поиске заявок. Попробуйте еще раз. Ошибка: <code>{e}</code>"
        try:
            await callback_query.message.edit_text(error_message, parse_mode=ParseMode.HTML)
        except Exception:
            await callback_query.message.answer(error_message, parse_mode=ParseMode.HTML)
    # finally:
    #     await state.clear()

# # --- Хендлер для остальных сообщений ---
# @router.message()
# async def echo_message(message: types.Message):
#     if message.text:
#         await message.answer(f"Я получил сообщение: <i>{escape_html(message.text)}</i>. Чтобы найти информацию, используйте команды /remains или /submissions.", parse_mode=ParseMode.HTML)
#     else:
#         await message.answer("Я получил сообщение, но оно не содержит текста.", parse_mode=ParseMode.HTML)
@router.message()
async def echo_message(message: types.Message):
    # Эта функция будет срабатывать только если нет других подходящих хендлеров
    # и состояние FSM не активно.
    if message.text:

        await message.answer("Для отримання потрібної інформації, скористайтеся кнопкою ' ☰ ', вона ліворуч", parse_mode=ParseMode.HTML)
    else:
        await message.answer("Я получил сообщение, но оно не содержит текста.")
