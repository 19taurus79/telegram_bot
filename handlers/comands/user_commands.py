from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.db.get_products import get_products, get_product_by_id
from utils.db.get_remains import get_remains
from utils.db.get_submissions import get_submissions





# Для логирования в хендлерах
import logging
# Если будете брать ADMIN_IDS из .env
import os

# Импортируем асинхронные функции для работы с базой данных пользователей
from middlewares.auth_middleware import set_user_allowed_status, get_user_info, get_all_users
# Создаем роутер для хендлеров
router = Router()
logger = logging.getLogger(__name__)

# Вариант 2: Чтение из .env (более гибко)
# Если вы используете этот вариант, добавьте ADMIN_TELEGRAM_IDS=123,456 в .env
admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "")
ADMIN_IDS = [int(id_str.strip()) for id_str in admin_ids_str.split(',') if id_str.strip()]

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

class BotStates(StatesGroup):
    waiting_for_nomenclature = State()
    waiting_for_product_selection = State()
    waiting_for_submissions_nomenclature = State()
    waiting_for_submissions_product_selection = State()


# Основное меню и команды
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


# --- Хендлер для команды /admin ---
@router.message(Command("admin"))
async def cmd_admin_menu(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("У Вас нема прав для доступу к адмін-меню.")
        logger.warning(
            f"Неавторизованная попытка доступа к /admin от {message.from_user.id}")
        return

    logger.info(f"Администратор {message.from_user.id} запросил админ-меню.")

    # Создаем админские команды для меню Telegram
    admin_commands = [
        # BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="list_users", description="👤 Список пользователей"),
        BotCommand(command="allow_user", description="✅ Разрешить доступ"),
        BotCommand(command="disallow_user", description="❌ Запретить доступ"),
        BotCommand(command="set_default_commands",
                   description="🔄 Вернуть обычные команды"),  # Для возврата
        # BotCommand(command="some_other_admin_command", description="Другая админ-команда"),
    ]

    # Устанавливаем команды для данного пользователя
    # scope=BotCommandScopeChat(chat_id=message.chat.id) означает, что команды видны только в этом чате для этого пользователя
    from aiogram.types import BotCommandScopeChat  # Импортируем для scope
    await message.bot.set_my_commands(
        admin_commands,
        scope=BotCommandScopeChat(chat_id=message.chat.id)
    )

    await message.answer(
        "Добро пожаловать в админ-меню! Ваши команды обновлены.\n"
        "Используйте /list_users, /allow_user ID, /disallow_user ID.\n"
        "Чтобы вернуться к обычным командам, нажмите /set_default_commands."
    )


# --- Хендлер для возврата к обычным командам ---
@router.message(Command("set_default_commands"))
async def cmd_set_default_commands(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    # Загружаем обычные команды (как в set_new_commands в main.py)
    default_commands = [
        BotCommand(command="remains", description="📦 Залишки"),
        BotCommand(command="orders", description="📄 Заявки на товар"),
        # BotCommand(command="help", description="❓ Получить помощь"),
        # BotCommand(command="settings", description="⚙️ Изменить настройки"),
        # BotCommand(command="about", description="ℹ️ О боте"),
        BotCommand(command="admin", description="🛠️ Меню адміна"),
        # <-- Важно: оставить команду админа
    ]
    from aiogram.types import BotCommandScopeChat  # Импортируем для scope
    await message.bot.set_my_commands(
        default_commands,
        scope=BotCommandScopeChat(chat_id=message.chat.id)
    )
    await message.answer("Команды бота сброшены на обычные.")
# --- НОВЫЕ АДМИНИСТРАТИВНЫЕ КОМАНДЫ ---

@router.message(Command("allow_user"))
async def cmd_allow_user(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этой команды.")
        logger.warning(f"Неавторизованная попытка /allow_user от {message.from_user.id}")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /allow_user Telegram_ID")
        return

    try:
        user_id_to_allow = int(args[1])
    except ValueError:
        await message.answer("Неверный формат Telegram ID. Используйте число.")
        return

    logger.info(f"Администратор {message.from_user.id} пытается разрешить доступ пользователю {user_id_to_allow}")
    if await set_user_allowed_status(user_id_to_allow, True):
        user_info = await get_user_info(user_id_to_allow)
        if user_info:
            name_display = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
            if user_info.get('username'):
                name_display += f" (@{user_info.get('username')})"

            final_display = name_display if name_display else f"Пользователю с ID: {user_id_to_allow}"
            await message.answer(f"{final_display} предоставлен доступ.")
            logger.info(f"Доступ разрешен пользователю {user_id_to_allow}")
        else:
            await message.answer(f"Пользователю с ID: {user_id_to_allow} предоставлен доступ (информация не найдена).")
            logger.info(f"Доступ разрешен пользователю {user_id_to_allow}, но инфо не найдено.")
    else:
        await message.answer(f"Не удалось предоставить доступ пользователю с ID: {user_id_to_allow}. Возможно, пользователь не найден в БД или ошибка.")
        logger.error(f"Ошибка при разрешении доступа пользователю {user_id_to_allow} администратором {message.from_user.id}")

@router.message(Command("disallow_user"))
async def cmd_disallow_user(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этой команды.")
        logger.warning(f"Неавторизованная попытка /disallow_user от {message.from_user.id}")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /disallow_user Telegram_ID")
        return

    try:
        user_id_to_disallow = int(args[1])
    except ValueError:
        await message.answer("Неверный формат Telegram ID. Используйте число.")
        return

    logger.info(f"Администратор {message.from_user.id} пытается запретить доступ пользователю {user_id_to_disallow}")
    if await set_user_allowed_status(user_id_to_disallow, False):
        await message.answer(f"Доступ пользователю с ID: {user_id_to_disallow} запрещен.")
        logger.info(f"Доступ запрещен пользователю {user_id_to_disallow}")
    else:
        await message.answer(f"Не удалось запретить доступ пользователю с ID: {user_id_to_disallow}. Возможно, пользователь не найден в БД или ошибка.")
        logger.error(f"Ошибка при запрете доступа пользователю {user_id_to_disallow} администратором {message.from_user.id}")

@router.message(Command("list_users"))
async def cmd_list_users(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этой команды.")
        logger.warning(f"Неавторизованная попытка /list_users от {message.from_user.id}")
        return

    logger.info(f"Администратор {message.from_user.id} запросил список пользователей.")
    users_info = await get_all_users()

    if not users_info:
        await message.answer("В базе данных нет зарегистрированных пользователей.")
        return

    response_parts = ["<b>Список пользователей:</b>\n\n"]
    for user_data in users_info:
        telegram_id = user_data.get('telegram_id')
        username = user_data.get('username')
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        is_allowed = user_data.get('is_allowed')
        reg_date = user_data.get('registration_date')
        last_act_date = user_data.get('last_activity_date')

        status = "✅ Разрешен" if is_allowed else "❌ Запрещен"

        user_display = f"ID: <code>{telegram_id}</code>\n"
        if username:
            user_display += f"Юзернейм: @{username}\n"

        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            user_display += f"Имя: {full_name}\n"

        user_display += f"Статус: {status}\n"
        user_display += f"Рег.: {reg_date.strftime('%Y-%m-%d %H:%M') if reg_date else 'N/A'}\n"
        user_display += f"Акт.: {last_act_date.strftime('%Y-%m-%d %H:%M') if last_act_date else 'N/A'}\n"
        response_parts.append(user_display + "\n")

    final_response = "".join(response_parts)

    MAX_MESSAGE_LENGTH = 4096
    if len(final_response) > MAX_MESSAGE_LENGTH:
        for i in range(0, len(final_response), MAX_MESSAGE_LENGTH):
            await message.answer(final_response[i:i+MAX_MESSAGE_LENGTH], parse_mode=ParseMode.HTML)
    else:
        await message.answer(final_response, parse_mode=ParseMode.HTML)

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


# Поиск остатков (`/remains`)
@router.message(Command("remains"))
async def cmd_remains_start(message: types.Message, state: FSMContext):
    await message.delete()
    await message.answer(
        "Будь ласка, вкажіть номенклатуру (або частину назви), яку ви хочете знайти:")
    await state.set_state(BotStates.waiting_for_nomenclature)


@router.message(BotStates.waiting_for_nomenclature)
async def process_nomenclature_query(message: types.Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.answer(
            "Ви нічого не ввели. Будь ласка, вкажіть номенклатуру.")
        return

    await message.answer(f"Шукаю продукти, що містять: <b>{query}</b>...",
                         parse_mode=ParseMode.HTML)

    try:
        product_entries = await get_products(query)

        if not product_entries:
            await message.answer(
                f"Не вдалося знайти продукти з номенклатурою, що містить: <b>{query}</b>.",
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
            "Знайдено декілька збігів. Будь ласка, оберіть потрібний продукт:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(BotStates.waiting_for_product_selection)
        await state.update_data(product_query=query)

    except Exception as e:
        print(f"Ошибка при поиске продуктов: {e}")
        await message.answer(
            f"Сталася помилка під час пошуку продуктів. Спробуйте ще раз. Помилка: `{e}`",
            parse_mode=ParseMode.HTML)
        await state.clear()


@router.callback_query(
    lambda c: c.data and c.data.startswith('select_product_remains:'))
async def process_product_selection(callback_query: types.CallbackQuery,
                                    state: FSMContext):
    """
    Обрабатывает выбор продукта из инлайн-клавиатуры и выводит остатки.
    Добавляет кнопку "Показать у кого под заявками".
    Общее количество (Бух. и Склад), количество под заявками и статус "свободный/нет" выводятся всегда.
    Если свободный остаток < 0, то отображается как 0.00.
    """
    await callback_query.answer("Ищу остатки...")
    product_uuid = callback_query.data.split(':')[1]

    await callback_query.message.answer("Обрано. Завантажую залишки...",
                                        parse_mode=ParseMode.HTML)

    try:
        product_entry = await get_product_by_id(product_uuid)
        if not product_entry:
            await callback_query.message.answer(
                "Продукт не знайдено в довіднику.")
            return

        remains_for_product = await get_remains(product_entry[0]['id'])
        submissions_for_product = await get_submissions(
            product_entry[0]['id'])  # Получаем данные по заявкам

        response_parts = []

        if remains_for_product:
            response_parts.append(
                f"📦 <b><u>*Залишки для продукту: {product_entry[0]['product']}*</u></b>\n")

            # Расчет общего количества (Бух. и Склад) - теперь всегда выводится
            total_buh = 0
            total_skl = 0
            for r in remains_for_product:
                try:
                    total_buh += float(r.get('buh', 0))
                    total_skl += float(r.get('skl', 0))
                except (ValueError, TypeError):
                    pass

            response_parts.append(
                f"  📊 <b>Загальна наявність (Бух.):</b> <code>{total_buh:.2f}</code>\n")
            response_parts.append(
                f"  📊 <b>Загальна наявність (Склад):</b> <code>{total_skl:.2f}</code>\n")

            # Расчет и вывод количества под заявками и свободного остатка (всегда)
            total_submissions_quantity = 0
            if submissions_for_product:
                for s in submissions_for_product:
                    try:
                        total_submissions_quantity += float(
                            s.get('different', 0))
                    except (ValueError, TypeError):
                        pass

            response_parts.append(
                f"  📝 <b>Під заявками:</b> <code>{total_submissions_quantity:.2f}</code>\n")

            free_stock = total_skl - total_submissions_quantity  # Используем total_skl, который теперь всегда подсчитан
            # Если свободный остаток меньше нуля, устанавливаем его в 0
            if free_stock < 0:
                free_stock = 0

            free_stock_status = "✅ Є вільний" if free_stock > 0 else "❌ Немає вільного"
            response_parts.append(
                f"  ➡️ <b>Вільний залишок:</b> <code>{free_stock:.2f}</code> ({free_stock_status})\n\n")

            # Добавляем заголовок "Детали по партиям" только если их больше одной
            if len(remains_for_product) > 1:
                response_parts.append("<b>Деталі по партіях:</b>\n")

            # Вывод по партиям
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
            response_parts.append("  _Залишків не знайдено._")

        final_response = "".join(response_parts)

        # Добавление кнопки "ПОКАЗАТЬ ЗАЯВКИ"
        builder = InlineKeyboardBuilder()

        await state.update_data(current_product_uuid=product_uuid)

        builder.button(
            text="👉 Показати у кого під заявками",
            callback_data="show_submissions_for_last_viewed_product"
        )

        if len(final_response) > 4000:
            await callback_query.message.answer(
                "Знайдено забагато результатів. Будь ласка, уточніть запит.")
        else:
            await callback_query.message.answer(
                final_response,
                reply_markup=builder.as_markup(),
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        print(f"Ошибка при поиске остатков по выбранному продукту: {e}")
        await callback_query.message.answer(
            f"Сталася помилка під час пошуку залишків. Спробуйте ще раз. Помилка: `{e}`",
            parse_mode=ParseMode.HTML)
    finally:
        pass


# Поиск заявок (`/orders`)
@router.message(Command("orders"))
async def cmd_submissions_start(message: types.Message, state: FSMContext):
    await message.delete()
    await message.answer(
        "Будь ласка, вкажіть номенклатуру (або частину назви) товару, за яким потрібно знайти заявки:",
        parse_mode=ParseMode.HTML)
    await state.set_state(BotStates.waiting_for_submissions_nomenclature)


@router.message(BotStates.waiting_for_submissions_nomenclature)
async def process_submissions_nomenclature_query(message: types.Message,
                                                 state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.answer(
            "Ви нічого не ввели. Будь ласка, вкажіть номенклатуру.",
            parse_mode=ParseMode.HTML)
        return

    try:
        await message.delete()
    except Exception as e:
        print(f"Не удалось удалить сообщение пользователя: {e}")

    await message.answer(f"Шукаю продукти, що містять: <b>{query}</b>...",
                         parse_mode=ParseMode.HTML)

    try:
        product_entries = await get_products(query)

        if not product_entries:
            await message.answer(
                f"Не вдалося знайти продукти з номенклатурою, що містить: <b>{query}</b>.",
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
            "Знайдено декілька збігів. Будь ласка, оберіть потрібний продукт:",
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.HTML
        )
        await state.set_state(
            BotStates.waiting_for_submissions_product_selection)
        await state.update_data(product_query=query)

    except Exception as e:
        print(f"Ошибка при поиске продуктов для заявок: {e}")
        await message.answer(
            f"Сталася помилка під час пошуку продуктів. Спробуйте ще раз. Помилка: <code>{e}</code>",
            parse_mode=ParseMode.HTML)
        await state.clear()


@router.callback_query(
    lambda c: c.data and c.data.startswith('select_product_submissions:'))
async def process_submissions_product_selection(
        callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    product_uuid = callback_query.data.split(':')[1]

    await callback_query.message.answer("Обрано. Шукаю заявки...",
                                        parse_mode=ParseMode.HTML)

    try:
        product_entry = await get_product_by_id(product_uuid)
        if not product_entry:
            await callback_query.message.answer(
                "Продукт не знайдено в довіднику.", parse_mode=ParseMode.HTML)
            return

        submissions_data = await get_submissions(product_entry[0]['id'])

        response_parts = []
        if submissions_data:
            response_parts.append(
                f"📄 <b>Заявки для продукту: {product_entry[0]['product']}</b>\n")

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
            response_parts.append("  <i>Заявок не знайдено.</i>\n")

        final_response = "".join(response_parts)

        if len(final_response) > 4000:
            await callback_query.message.answer(
                "Знайдено забагато результатів. Будь ласка, уточніть запит.",
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
        error_message = f"Сталася помилка під час пошуку заявок. Спробуйте ще раз. Помилка: <code>{e}</code>"
        try:
            await callback_query.message.edit_text(error_message,
                                                   parse_mode=ParseMode.HTML)
        except Exception:
            await callback_query.message.answer(error_message,
                                                parse_mode=ParseMode.HTML)


# Новый хендлер для перехода к заявкам из остатков
@router.callback_query(
    lambda c: c.data == 'show_submissions_for_last_viewed_product')
async def show_submissions_for_product(callback_query: types.CallbackQuery,
                                       state: FSMContext):
    """
    Обрабатывает нажатие кнопки "Показать у кого под заявками" из сообщения с остатками.
    Получает UUID продукта из FSMContext.
    """
    await callback_query.answer("Завантажую заявки...")

    data = await state.get_data()
    product_uuid = data.get('current_product_uuid')

    if not product_uuid:
        await callback_query.message.answer(
            "Ошибка: Не удалось найти информацию о товаре. Пожалуйста, начните поиск остатков заново.",
            parse_mode=ParseMode.HTML)
        return

    await callback_query.message.answer("Обрано. Завантажую заявки...",
                                        parse_mode=ParseMode.HTML)

    try:
        product_entry = await get_product_by_id(product_uuid)
        if not product_entry:
            await callback_query.message.answer(
                "Продукт не знайдено в довіднику.", parse_mode=ParseMode.HTML)
            return

        submissions_data = await get_submissions(product_entry[0]['id'])

        response_parts = []
        if submissions_data:
            response_parts.append(
                f"📄 <b>Заявки для продукту: {product_entry[0]['product']}</b>\n")

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
            response_parts.append("  <i>Заявок не знайдено.</i>\n")

        final_response = "".join(response_parts)

        if len(final_response) > 4000:
            await callback_query.message.answer(
                "Знайдено забагато результатів. Будь ласка, уточніть запит.",
                parse_mode=ParseMode.HTML)
        else:
            await callback_query.message.answer(final_response,
                                                parse_mode=ParseMode.HTML)

    except Exception as e:
        print(
            f"Ошибка при поиске заявок по выбранному продукту из остатков: {e}")
        await callback_query.message.answer(
            f"Сталася помилка під час пошуку заявок. Спробуйте ще раз. Помилка: <code>{e}</code>",
            parse_mode=ParseMode.HTML)
    finally:
        pass


# Обработка остальных сообщений
@router.message()
async def echo_message(message: types.Message):
    if message.text:
        await message.answer(
            "Сюди приходять тільки оповіщення. Спілкування в цьому чаті неможливе.",
            parse_mode=ParseMode.HTML)
    else:
        await message.answer("Ви отримали сповіщення, але воно не містить тексту.")