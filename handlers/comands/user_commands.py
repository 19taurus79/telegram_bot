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
    waiting_for_product_selection = State()
    waiting_for_submissions_nomenclature = State()
    waiting_for_submissions_product_selection = State()
    # Дополнительное состояние для временного хранения ID продукта, если нужно
    # Хотя в данном случае мы можем использовать данные текущего состояния.





## Основное меню и команды

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Показать мои данные",
                              callback_data="show_my_data")],
        [InlineKeyboardButton(text="О боте", callback_data="about_bot")],
        [InlineKeyboardButton(text="Помощь", callback_data="help_info")],
        [InlineKeyboardButton(text="Посетить наш сайт",
                              url="https://www.example.com")]
    ])

    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n\n"
        "Я могу многое! Выбери одну из опций ниже:",
        reply_markup=keyboard
    )


@router.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Показать мои данные",
                              callback_data="show_my_data")],
        [InlineKeyboardButton(text="О боте", callback_data="about_bot")],
        [InlineKeyboardButton(text="Помощь", callback_data="help_info")],
        [InlineKeyboardButton(text="Посетить наш сайт",
                              url="https://www.example.com")]
    ])
    await message.answer("Вот что я могу предложить:", reply_markup=keyboard)


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Я могу помочь тебе с этим и тем. Попробуй отправить мне сообщение или выбери опцию из меню!")





## Поиск остатков (`/remains`)

@router.message(Command("remains"))
async def cmd_remains_start(message: types.Message, state: FSMContext):
    await message.delete()
    await message.answer(
        "Пожалуйста, укажите номенклатуру (или часть названия), которую вы хотите найти:")
    await state.set_state(BotStates.waiting_for_nomenclature)


@router.message(BotStates.waiting_for_nomenclature)
async def process_nomenclature_query(message: types.Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.answer(
            "Вы ничего не ввели. Пожалуйста, укажите номенклатуру.")
        return

    await message.answer(f"Ищу продукты, содержащие: <b>{query}</b>...",
                         parse_mode=ParseMode.HTML)

    try:
        product_entries = await get_products(query)

        if not product_entries:
            await message.answer(
                f"Не удалось найти продукты с номенклатурой, содержащей: <b>{query}</b>.",
                parse_mode=ParseMode.HTML)
            await state.clear()
            return

        builder = InlineKeyboardBuilder()
        for product_entry in product_entries:
            builder.button(
                text=product_entry['product'],
                callback_data=f"select_product_remains:{product_entry['id']}"
            )
        builder.adjust(1)

        await message.answer(
            "Найдено несколько совпадений. Пожалуйста, выберите нужный продукт:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(BotStates.waiting_for_product_selection)
        await state.update_data(product_query=query)

    except Exception as e:
        print(f"Ошибка при поиске продуктов: {e}")
        await message.answer(
            f"Произошла ошибка при поиске продуктов. Попробуйте еще раз. Ошибка: `{e}`",
            parse_mode=ParseMode.HTML)
        await state.clear()


@router.callback_query(
    lambda c: c.data and c.data.startswith('select_product_remains:'))
async def process_product_selection(callback_query: types.CallbackQuery,
                                    state: FSMContext):
    """
    Обрабатывает выбор продукта из инлайн-клавиатуры и выводит остатки.
    Добавляет кнопку "Показать у кого под заявками".
    """
    await callback_query.answer("Ищу остатки...")
    product_uuid = callback_query.data.split(':')[1]

    await callback_query.message.answer("Выбрано. Загружаю остатки...",
                                        parse_mode=ParseMode.HTML)

    try:
        product_entry = await get_product_by_id(product_uuid)
        if not product_entry:
            await callback_query.message.answer(
                "Продукт не найден в справочнике.")
            return

        remains_for_product = await get_remains(product_entry[0]['id'])

        response_parts = []
        if remains_for_product:
            response_parts.append(
                f"📦 <b><u>*Остатки для продукта: {product_entry[0]['product']}*</u></b>\n")
            for r in remains_for_product:
                if r['line_of_business'] in ['Власне виробництво насіння',
                                             'Насіння']:
                    response_parts.append(
                        f"  - Партія: {r['nomenclature_series']}\n"
                        f"  - МТН: {r['mtn']}\n"
                        f"  - Страна походження: {r['origin_country']}\n"
                        f"  - Схожість: {r['germination']}\n"
                        f"  - Рік урожаю: {r['crop_year']}\n"
                        f"  - Вага: {r['weight']}\n"
                        f"  - Наявність (Бух.): {r['buh']}\n"
                        f"  - Наявність (Склад): {r['skl']}\n\n"
                    )
                else:
                    response_parts.append(
                        f"  - Партія: {r['nomenclature_series']}\n"
                        f"  - Наявність (Бух.): {r['buh']}\n"
                        f"  - Наявність (Склад): {r['skl']}\n\n"
                    )
        else:
            response_parts.append(f"📦 *Продукт: {product_entry[0]['product']}*")
            response_parts.append("  _Остатков не найдено._")

        final_response = "".join(
            response_parts)  # Changed from "\n".join() to "".join() for consistency with HTML

        # --- ДОБАВЛЕНИЕ КНОПКИ "ПОКАЗАТЬ ЗАЯВКИ" ---
        builder = InlineKeyboardBuilder()

        # СОХРАНЯЕМ product_uuid в состоянии FSM
        await state.update_data(current_product_uuid=product_uuid)

        # CALLBACK_DATA ТЕПЕРЬ ПРОСТО МАРКЕР, БЕЗ UUID, ЧТОБЫ УЛОЖИТЬСЯ В 64 БАЙТА
        builder.button(
            text="👉 Показать у кого под заявками",
            callback_data="show_submissions_for_last_viewed_product"
            # Сокращенная callback_data
        )

        if len(final_response) > 4000:
            await callback_query.message.answer(
                "Найдено слишком много результатов. Пожалуйста, уточните запрос.")
        else:
            await callback_query.message.answer(
                final_response,
                reply_markup=builder.as_markup(),
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        print(f"Ошибка при поиске остатков по выбранному продукту: {e}")
        await callback_query.message.answer(
            f"Произошла ошибка при поиске остатков. Попробуйте еще раз. Ошибка: `{e}`",
            parse_mode=ParseMode.HTML)
    finally:
        pass




## Поиск заявок (`/orders`)

@router.message(Command("orders"))
async def cmd_submissions_start(message: types.Message, state: FSMContext):
    await message.delete()
    await message.answer(
        "Пожалуйста, укажите номенклатуру (или часть названия) товара, по которому нужно найти заявки:",
        parse_mode=ParseMode.HTML)
    await state.set_state(BotStates.waiting_for_submissions_nomenclature)


@router.message(BotStates.waiting_for_submissions_nomenclature)
async def process_submissions_nomenclature_query(message: types.Message,
                                                 state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.answer(
            "Вы ничего не ввели. Пожалуйста, укажите номенклатуру.",
            parse_mode=ParseMode.HTML)
        return

    try:
        await message.delete()
    except Exception as e:
        print(f"Не удалось удалить сообщение пользователя: {e}")

    await message.answer(f"Ищу продукты, содержащие: <b>{query}</b>...",
                         parse_mode=ParseMode.HTML)

    try:
        product_entries = await get_products(query)

        if not product_entries:
            await message.answer(
                f"Не удалось найти продукты с номенклатурой, содержащей: <b>{query}</b>.",
                parse_mode=ParseMode.HTML)
            await state.clear()
            return

        builder = InlineKeyboardBuilder()
        for product_entry in product_entries:
            button_text = product_entry['product']
            builder.button(
                text=button_text,
                callback_data=f"select_product_submissions:{product_entry['id']}"
            )
        builder.adjust(1)

        await message.answer(
            "Найдено несколько совпадений. Пожалуйста, выберите нужный продукт:",
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.HTML
        )
        await state.set_state(
            BotStates.waiting_for_submissions_product_selection)
        await state.update_data(product_query=query)

    except Exception as e:
        print(f"Ошибка при поиске продуктов для заявок: {e}")
        await message.answer(
            f"Произошла ошибка при поиске продуктов. Попробуйте еще раз. Ошибка: <code>{e}</code>",
            parse_mode=ParseMode.HTML)
        await state.clear()


@router.callback_query(
    lambda c: c.data and c.data.startswith('select_product_submissions:'))
async def process_submissions_product_selection(
        callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    product_uuid = callback_query.data.split(':')[1]

    await callback_query.message.answer("Выбрано. Ищу заявки...",
                                        parse_mode=ParseMode.HTML)

    try:
        product_entry = await get_product_by_id(product_uuid)
        if not product_entry:
            await callback_query.message.answer(
                "Продукт не найден в справочнике.", parse_mode=ParseMode.HTML)
            return

        submissions_data = await get_submissions(product_entry[0]['id'])

        response_parts = []
        if submissions_data:
            response_parts.append(
                f"📄 <b>Заявки для продукта: {product_entry[0]['product']}</b>\n")

            for s in submissions_data:
                response_parts.append(
                    f"  - Контрагент: {s['client']}\n"
                    f"  - Менеджер: {s['manager']}\n"
                    f"  - Доповнення: {s['contract_supplement']}\n"
                    f"  - Кількість: {s['different']}\n\n"
                )
        else:
            response_parts.append(
                f"📄 <b>Продукт: {product_entry[0]['product']}</b>\n")
            response_parts.append("  <i>Заявок не найдено.</i>\n")

        final_response = "".join(response_parts)

        if len(final_response) > 4000:
            await callback_query.message.answer(
                "Найдено слишком много результатов. Пожалуйста, уточните запрос.",
                parse_mode=ParseMode.HTML)
        else:
            try:
                await callback_query.message.answer(final_response,
                                                    parse_mode=ParseMode.HTML)
            except Exception as e:
                print(f"Не удалось отредактировать финальное сообщение: {e}")
                await callback_query.message.answer(final_response,
                                                    parse_mode=ParseMode.HTML)

    except Exception as e:
        print(f"Ошибка при поиске заявок по выбранному продукту: {e}")
        error_message = f"Произошла ошибка при поиске заявок. Попробуйте еще раз. Ошибка: <code>{e}</code>"
        try:
            await callback_query.message.edit_text(error_message,
                                                   parse_mode=ParseMode.HTML)
        except Exception:
            await callback_query.message.answer(error_message,
                                                parse_mode=ParseMode.HTML)





## Новый хендлер для перехода к заявкам из остатков (МОДИФИЦИРОВАН)

@router.callback_query(
    lambda c: c.data == 'show_submissions_for_last_viewed_product')
async def show_submissions_for_product(callback_query: types.CallbackQuery,
                                       state: FSMContext):
    """
    Обрабатывает нажатие кнопки "Показать у кого под заявками" из сообщения с остатками.
    Получает UUID продукта из FSMContext.
    """
    await callback_query.answer("Загружаю заявки...")

    # Извлекаем UUID продукта из FSMContext
    data = await state.get_data()
    product_uuid = data.get('current_product_uuid')

    if not product_uuid:
        await callback_query.message.answer(
            "Ошибка: Не удалось найти информацию о товаре. Пожалуйста, начните поиск остатков заново.",
            parse_mode=ParseMode.HTML)
        return

    await callback_query.message.answer("Выбрано. Загружаю заявки...",
                                        parse_mode=ParseMode.HTML)

    try:
        product_entry = await get_product_by_id(product_uuid)
        if not product_entry:
            await callback_query.message.answer(
                "Продукт не найден в справочнике.", parse_mode=ParseMode.HTML)
            return

        submissions_data = await get_submissions(product_entry[0]['id'])

        response_parts = []
        if submissions_data:
            response_parts.append(
                f"📄 <b>Заявки для продукта: {product_entry[0]['product']}</b>\n")

            for s in submissions_data:
                response_parts.append(
                    f"  - Контрагент: {s['client']}\n"
                    f"  - Менеджер: {s['manager']}\n"
                    f"  - Доповнення: {s['contract_supplement']}\n"
                    f"  - Кількість: {s['different']}\n\n"
                )
        else:
            response_parts.append(
                f"📄 <b>Продукт: {product_entry[0]['product']}</b>\n")
            response_parts.append("  <i>Заявок не найдено.</i>\n")

        final_response = "".join(response_parts)

        if len(final_response) > 4000:
            await callback_query.message.answer(
                "Найдено слишком много результатов. Пожалуйста, уточните запрос.",
                parse_mode=ParseMode.HTML)
        else:
            await callback_query.message.answer(final_response,
                                                parse_mode=ParseMode.HTML)

    except Exception as e:
        print(
            f"Ошибка при поиске заявок по выбранному продукту из остатков: {e}")
        await callback_query.message.answer(
            f"Произошла ошибка при поиске заявок. Попробуйте еще раз. Ошибка: <code>{e}</code>",
            parse_mode=ParseMode.HTML)
    finally:
        pass





## Обработка остальных сообщений

@router.message()
async def echo_message(message: types.Message):
    if message.text:
        await message.answer(
            "Для отримання потрібної інформації, скористайтеся кнопкою ' ☰ ', вона ліворуч",
            parse_mode=ParseMode.HTML)
    else:
        await message.answer("Я получил сообщение, но оно не содержит текста.")