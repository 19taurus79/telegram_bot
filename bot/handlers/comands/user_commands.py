import logging
import os

from aiogram import Router, types
from aiogram.enums import ParseMode # Используем ParseMode.HTML
from aiogram.filters import CommandStart, Command, StateFilter # Добавляем StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeChat # Добавляем BotCommandScopeChat
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- ИМПОРТЫ ФУНКЦИЙ БД ---
# Убедитесь, что пути к вашим файлам с функциями БД корректны
from utils.db.get_products import get_products, get_product_by_id
from utils.db.get_remains import get_remains
from utils.db.get_submissions import get_submissions

# --- ИМПОРТЫ ФУНКЦИЙ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ---
from middlewares.auth_middleware import set_user_allowed_status, get_user_info, get_all_users


router = Router()
logger = logging.getLogger(__name__)

# --- НАСТРОЙКИ АДМИНИСТРАТОРОВ ---
# Чтение ID администраторов из .env (более гибкий и безопасный подход)
admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "")
# Преобразуем строку ID в список целых чисел
ADMIN_IDS = [int(id_str.strip()) for id_str in admin_ids_str.split(',') if id_str.strip()]

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    return user_id in ADMIN_IDS

# --- ОПРЕДЕЛЕНИЕ СОСТОЯНИЙ FSM ---
class BotStates(StatesGroup):
    waiting_for_nomenclature = State()
    waiting_for_product_selection = State() # Это состояние не будет использоваться для строгого перехода
    waiting_for_submissions_nomenclature = State()
    waiting_for_submissions_product_selection = State() # Это состояние не будет использоваться для строгого перехода
    # Добавляем состояние для ожидания ID пользователя в админке, если нужно
    waiting_for_user_id_to_allow = State()
    waiting_for_user_id_to_disallow = State()


# --- БЛОК 1: ВСЕ КОМАНДНЫЕ ХЕНДЛЕРЫ ---
# Эти хендлеры должны быть в самом начале файла `handlers/comands.py`,
# сразу после объявления `router = Router()` и `class BotStates(...)`.
# Они будут "перехватывать" команды, даже если бот находится в FSM-состоянии,
# благодаря тому, что они зарегистрированы раньше.

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext): # Добавляем state
    """Обрабатывает команду /start, очищает состояние и показывает главное меню."""
    await state.clear() # Очищаем любое активное FSM-состояние
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Показать мои данные", callback_data="show_my_data")],
        [InlineKeyboardButton(text="О боте", callback_data="about_bot")],
        [InlineKeyboardButton(text="Помощь", callback_data="help_info")],
        [InlineKeyboardButton(text="Посетить наш сайт", url="https://www.example.com")]
    ])
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n\n"
        "Я могу многое! Выбери одну из опций ниже:",
        reply_markup=keyboard
    )
    logger.info(f"User {message.from_user.id} executed /start. State cleared.")


@router.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext): # Добавляем state
    """Обрабатывает команду /menu, очищает состояние и показывает главное меню."""
    await state.clear() # Очищаем любое активное FSM-состояние
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Показать мои данные", callback_data="show_my_data")],
        [InlineKeyboardButton(text="О боте", callback_data="about_bot")],
        [InlineKeyboardButton(text="Помощь", callback_data="help_info")],
        [InlineKeyboardButton(text="Посетить наш сайт", url="https://www.example.com")]
    ])
    await message.answer("Вот что я могу предложить:", reply_markup=keyboard)
    logger.info(f"User {message.from_user.id} executed /menu. State cleared.")


@router.message(Command("help"))
async def cmd_help(message: types.Message, state: FSMContext): # Добавляем state
    """Обрабатывает команду /help, очищает состояние."""
    await state.clear() # Очищаем любое активное FSM-состояние
    await message.answer(
        "Я могу помочь тебе с этим и тем. Попробуй отправить мне сообщение или выбери опцию из меню!")
    logger.info(f"User {message.from_user.id} executed /help. State cleared.")


# --- СПЕЦИАЛЬНЫЕ КОМАНДЫ ДЛЯ НАЧАЛА ДИАЛОГОВ (Остатки, Заявки) ---
# Эти хендлеры также должны быть выше, чем FSM-хендлеры, обрабатывающие общий текст.

@router.message(Command("remains"))
async def cmd_remains_start(message: types.Message, state: FSMContext):
    """Начинает режим поиска остатков, очищает состояние и устанавливает новое."""
    await state.clear() # Очищаем любое предыдущее состояние
    try:
        await message.delete() # Пытаемся удалить сообщение пользователя с командой
    except Exception as e:
        logger.warning(f"Failed to delete user message on /remains: {e}")
    await message.answer(
        "📦 <b>Режим пошуку залишків</b>\nБудь ласка, вкажіть номенклатуру (або частину назви), яку ви хочете знайти:",
        parse_mode=ParseMode.HTML # Использование HTML
    )
    await state.set_state(BotStates.waiting_for_nomenclature)
    logger.info(f"User {message.from_user.id} entered /remains mode.")


@router.message(Command("orders"))
async def cmd_submissions_start(message: types.Message, state: FSMContext):
    """Начинает режим поиска заявок, очищает состояние и устанавливает новое."""
    await state.clear() # Очищаем любое предыдущее состояние
    try:
        await message.delete() # Пытаемся удалить сообщение пользователя с командой
    except Exception as e:
        logger.warning(f"Failed to delete user message on /orders: {e}")
    await message.answer(
        "📄 <b>Режим пошуку заявок</b>\nБудь ласка, вкажіть номенклатуру (або частину назви) товару, за яким потрібно знайти заявки:",
        parse_mode=ParseMode.HTML # Использование HTML
    )
    await state.set_state(BotStates.waiting_for_submissions_nomenclature)
    logger.info(f"User {message.from_user.id} entered /orders mode.")


# --- ХЕНДЛЕРЫ АДМИН-КОМАНД ---
# Эти хендлеры также должны быть расположены выше, чем FSM-хендлеры,
# которые обрабатывают общий текст, чтобы гарантировать их срабатывание.

@router.message(Command("admin"))
async def cmd_admin_menu(message: types.Message, state: FSMContext): # Добавляем state
    """Обрабатывает команду /admin, очищает состояние и показывает админ-меню."""
    await state.clear() # Очищаем любое активное FSM-состояние при входе в админ-меню

    if not is_admin(message.from_user.id):
        await message.answer("У Вас нема прав для доступу к адмін-меню.")
        logger.warning(
            f"Неавторизованная попытка доступа к /admin от {message.from_user.id}")
        return

    logger.info(f"Администратор {message.from_user.id} запросил админ-меню.")

    # Создаем админские команды для меню Telegram
    admin_commands = [
        BotCommand(command="list_users", description="👤 Список пользователей"),
        BotCommand(command="allow_user", description="✅ Разрешить доступ"),
        BotCommand(command="disallow_user", description="❌ Запретить доступ"),
        BotCommand(command="set_default_commands",
                   description="🔄 Вернуть обычные команды"),
    ]

    # Устанавливаем команды для данного пользователя (чтобы он видел их в меню)
    await message.bot.set_my_commands(
        admin_commands,
        scope=BotCommandScopeChat(chat_id=message.chat.id)
    )

    # *** ВОЗВРАЩЕНО ИСПОЛЬЗОВАНИЕ ParseMode.HTML ***
    await message.answer(
        "🛠️ <b>Добро пожаловать в админ-меню! Ваши команды обновлены.</b>\n"
        "Используйте /list_users, /allow_user ID, /disallow_user ID.\n"
        "Чтобы вернуться к обычным командам, нажмите /set_default_commands.",
        parse_mode=ParseMode.HTML # Используем HTML
    )


@router.message(Command("set_default_commands"))
async def cmd_set_default_commands(message: types.Message, state: FSMContext): # Добавляем state
    """Обрабатывает команду /set_default_commands, сбрасывает команды и очищает состояние."""
    await state.clear() # Очищаем любое активное FSM-состояние

    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    # Загружаем обычные команды (как в set_new_commands в main.py)
    default_commands = [
        BotCommand(command="remains", description="📦 Залишки"),
        BotCommand(command="orders", description="📄 Заявки на товар"),
        BotCommand(command="admin", description="🛠️ Меню адміна"), # Важно: оставляем команду админа
    ]

    # Устанавливаем команды для данного пользователя
    await message.bot.set_my_commands(
        default_commands,
        scope=BotCommandScopeChat(chat_id=message.chat.id)
    )
    await message.answer("🔄 <b>Команды бота сброшены на обычные.</b>", parse_mode=ParseMode.HTML)
    logger.info(f"Admin {message.from_user.id} reset commands to default.")


@router.message(Command("allow_user"))
async def cmd_allow_user(message: types.Message, state: FSMContext):
    """Позволяет администратору разрешить доступ пользователю по ID."""
    await state.clear() # Очищаем состояние
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этой команды.")
        logger.warning(f"Неавторизованная попытка /allow_user от {message.from_user.id}")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: <code>/allow_user Telegram_ID</code>", parse_mode=ParseMode.HTML)
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

            final_display = name_display if name_display else f"Пользователю с ID: <code>{user_id_to_allow}</code>"
            await message.answer(f"✅ {final_display} <b>предоставлен доступ.</b>", parse_mode=ParseMode.HTML)
            logger.info(f"Доступ разрешен пользователю {user_id_to_allow}")
        else:
            await message.answer(f"✅ <b>Пользователю с ID:</b> <code>{user_id_to_allow}</code> <b>предоставлен доступ (информация не найдена).</b>", parse_mode=ParseMode.HTML)
            logger.info(f"Доступ разрешен пользователю {user_id_to_allow}, но инфо не найдено.")
    else:
        await message.answer(f"❌ <b>Не удалось предоставить доступ пользователю с ID:</b> <code>{user_id_to_allow}</code>. Возможно, пользователь не найден в БД или ошибка.", parse_mode=ParseMode.HTML)
        logger.error(f"Ошибка при разрешении доступа пользователю {user_id_to_allow} администратором {message.from_user.id}")


@router.message(Command("disallow_user"))
async def cmd_disallow_user(message: types.Message, state: FSMContext):
    """Позволяет администратору запретить доступ пользователю по ID."""
    await state.clear() # Очищаем состояние
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этой команды.")
        logger.warning(f"Неавторизованная попытка /disallow_user от {message.from_user.id}")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: <code>/disallow_user Telegram_ID</code>", parse_mode=ParseMode.HTML)
        return

    try:
        user_id_to_disallow = int(args[1])
    except ValueError:
        await message.answer("Неверный формат Telegram ID. Используйте число.")
        return

    logger.info(f"Администратор {message.from_user.id} пытается запретить доступ пользователю {user_id_to_disallow}")
    if await set_user_allowed_status(user_id_to_disallow, False):
        await message.answer(f"❌ <b>Доступ пользователю с ID:</b> <code>{user_id_to_disallow}</code> <b>запрещен.</b>", parse_mode=ParseMode.HTML)
        logger.info(f"Доступ запрещен пользователю {user_id_to_disallow}")
    else:
        await message.answer(f"❓ <b>Не удалось запретить доступ пользователю с ID:</b> <code>{user_id_to_disallow}</code>. Возможно, пользователь не найден в БД или ошибка.", parse_mode=ParseMode.HTML)
        logger.error(f"Ошибка при запрете доступа пользователю {user_id_to_disallow} администратором {message.from_user.id}")


@router.message(Command("list_users"))
async def cmd_list_users(message: types.Message, state: FSMContext): # Добавляем state
    """Позволяет администратору просмотреть список пользователей."""
    await state.clear() # Очищаем состояние
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этой команды.")
        logger.warning(f"Неавторизованная попытка /list_users от {message.from_user.id}")
        return

    logger.info(f"Администратор {message.from_user.id} запросил список пользователей.")
    users_info = await get_all_users()

    if not users_info:
        await message.answer("В базе данных нет зарегистрированных пользователей.")
        return

    response_parts = ["<b>Список пользователей:</b>\n\n"] # Использование HTML
    for user_data in users_info:
        telegram_id = user_data.get('telegram_id')
        username = user_data.get('username')
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        is_allowed = user_data.get('is_allowed')
        reg_date = user_data.get('registration_date')
        last_act_date = user_data.get('last_activity_date')

        status = "✅ Разрешен" if is_allowed else "❌ Запрещен"

        user_display = f"ID: <code>{telegram_id}</code>\n" # Использование HTML-тега <code>
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

    MAX_MESSAGE_LENGTH = 4096 # Для HTML это может быть больше, но 4096 безопаснее
    if len(final_response) > MAX_MESSAGE_LENGTH:
        # Разбиваем длинное сообщение на части
        for i in range(0, len(final_response), MAX_MESSAGE_LENGTH):
            await message.answer(final_response[i:i+MAX_MESSAGE_LENGTH], parse_mode=ParseMode.HTML)
    else:
        await message.answer(final_response, parse_mode=ParseMode.HTML)


# --- БЛОК 2: ХЕНДЛЕРЫ FSM-СОСТОЯНИЙ, ОБРАБАТЫВАЮЩИЕ ТЕКСТОВЫЙ ВВОД ---
# Эти хендлеры расположены ПОСЛЕ всех командных хендлеров.
# Фильтры `~Command(...)` говорят: "Обрабатывать текст, только если это НЕ команда."

@router.message(BotStates.waiting_for_nomenclature,
                ~Command("orders"), ~Command("menu"), ~CommandStart(), ~Command("help"), ~Command("admin"),
                ~Command("allow_user"), ~Command("disallow_user"), ~Command("list_users"), ~Command("set_default_commands"))
async def process_nomenclature_query(message: types.Message, state: FSMContext):
    """Обрабатывает ввод номенклатуры для поиска остатков."""
    logger.info(f"User {message.from_user.id} in 'waiting_for_nomenclature' state, query: '{message.text}'")
    query = message.text.strip()
    if not query:
        await message.answer(
            "📦 <b>Режим пошуку залишків</b>\nВи нічого не ввели. Будь ласка, вкажіть номенклатуру.",
            parse_mode=ParseMode.HTML
        )
        return

    await message.answer(f"📦 <b>Режим пошуку залишків</b>\nШукаю продукти, що містять: <b>{query}</b>...",
                         parse_mode=ParseMode.HTML)

    try:
        product_entries = await get_products(query)

        if not product_entries:
            await message.answer(
                f"📦 <b>Режим пошуку залишків</b>\nНе вдалося знайти продукти з номенклатурою, що містить: <b>{query}</b>.\n"
                "Будь ласка, спробуйте ще раз або виберіть іншу команду.",
                parse_mode=ParseMode.HTML)
            return

        builder = InlineKeyboardBuilder()
        for product_entry in product_entries:
            builder.button(
                text=product_entry['product'],
                callback_data=f"select_product_remains:{product_entry['id']}"
            )
        builder.adjust(1)

        await message.answer(
            "📦 <b>Режим пошуку залишків</b>\nЗнайдено декілька збігів. Будь ласка, оберіть потрібний продукт:",
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.HTML
        )
        await state.update_data(product_query=query)

    except Exception as e:
        logger.error(f"Error searching products for remains for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer(
            f"📦 <b>Режим пошуку залишків</b>\nСталася помилка під час пошуку продуктів. Спробуйте ще раз. Помилка: <code>{e}</code>",
            parse_mode=ParseMode.HTML)


@router.message(BotStates.waiting_for_submissions_nomenclature,
                ~Command("remains"), ~Command("menu"), ~CommandStart(), ~Command("help"), ~Command("admin"),
                ~Command("allow_user"), ~Command("disallow_user"), ~Command("list_users"), ~Command("set_default_commands"))
async def process_submissions_nomenclature_query(message: types.Message,
                                                 state: FSMContext):
    """Обрабатывает ввод номенклатуры для поиска заявок."""
    logger.info(f"User {message.from_user.id} in 'waiting_for_submissions_nomenclature' state, query: '{message.text}'")
    query = message.text.strip()
    if not query:
        await message.answer(
            "📄 <b>Режим пошуку заявок</b>\nВи нічого не ввели. Будь ласка, вкажіть номенклатуру.",
            parse_mode=ParseMode.HTML)
        return

    try:
        await message.delete() # Пытаемся удалить сообщение пользователя
    except Exception as e:
        logger.warning(f"Failed to delete user message in submissions query: {e}")

    await message.answer(f"📄 <b>Режим пошуку заявок</b>\nШукаю продукти, що містять: <b>{query}</b>...",
                         parse_mode=ParseMode.HTML)

    try:
        product_entries = await get_products(query)

        if not product_entries:
            await message.answer(
                f"📄 <b>Режим пошуку заявок</b>\nНе вдалося знайти продукти з номенклатурою, що містить: <b>{query}</b>.\n"
                "Будь ласка, спробуйте ще раз або виберіть іншу команду.",
                parse_mode=ParseMode.HTML)
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
            "📄 <b>Режим пошуку заявок</b>\nЗнайдено декілька збігів. Будь ласка, оберіть потрібний продукт:",
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.HTML
        )
        await state.update_data(product_query=query)

    except Exception as e:
        logger.error(f"Error searching products for submissions for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer(
            f"📄 <b>Режим пошуку заявок</b>\nСталася помилка під час пошуку продуктів. Спробуйте ще раз. Помилка: <code>{e}</code>",
            parse_mode=ParseMode.HTML)


# --- БЛОК 3: CALLBACK-ХЕНДЛЕРЫ ---
# Эти хендлеры могут находиться ниже. Их порядок обычно менее критичен,
# так как они срабатывают на нажатия кнопок, а не на текстовые сообщения.
# Добавляем логирование и ParseMode.HTML

@router.callback_query(
    lambda c: c.data and c.data.startswith('select_product_remains:'))
async def process_product_selection(callback_query: types.CallbackQuery,
                                    state: FSMContext):
    """
    Обрабатывает выбор продукта из инлайн-клавиатуры для остатков.
    Выводит остатки и кнопку "Показать у кого под заявками".
    """
    logger.info(f"User {callback_query.from_user.id} selected product for remains: {callback_query.data}")
    await callback_query.answer("Ищу остатки...")
    product_uuid = callback_query.data.split(':')[1]

    await callback_query.message.answer("📦 <b>Режим пошуку залишків</b>\nОбрано. Завантажую залишки...",
                                        parse_mode=ParseMode.HTML)

    try:
        product_entry = await get_product_by_id(product_uuid)
        if not product_entry:
            await callback_query.message.answer(
                "📦 <b>Режим пошуку залишків</b>\nПродукт не знайдено в довіднику.",
                parse_mode=ParseMode.HTML)
            await state.set_state(BotStates.waiting_for_nomenclature) # Возвращаемся в режим ввода номенклатуры
            return

        remains_for_product = await get_remains(product_entry[0]['id'])
        submissions_for_product = await get_submissions(product_entry[0]['id'])

        response_parts = []
        if remains_for_product:
            response_parts.append(
                f"📦 <b><u>Залишки для продукту: {product_entry[0]['product']}</u></b>\n") # Использование HTML

            total_buh = 0
            total_skl = 0
            for r in remains_for_product:
                try:
                    total_buh += float(r.get('buh', 0))
                    total_skl += float(r.get('skl', 0))
                except (ValueError, TypeError):
                    pass

            response_parts.append(
                f"  📊 <b>Загальна наявність (Бух.):</b> <code>{total_buh:.2f}</code>\n") # Использование HTML
            response_parts.append(
                f"  📊 <b>Загальна наявність (Склад):</b> <code>{total_skl:.2f}</code>\n") # Использование HTML

            total_submissions_quantity = 0
            if submissions_for_product:
                for s in submissions_for_product:
                    try:
                        total_submissions_quantity += float(s.get('different', 0))
                    except (ValueError, TypeError):
                        pass

            response_parts.append(
                f"  📝 <b>Під заявками:</b> <code>{total_submissions_quantity:.2f}</code>\n") # Использование HTML

            free_stock = total_skl - total_submissions_quantity
            if free_stock < 0:
                free_stock = 0

            free_stock_status = "✅ Є вільний" if free_stock > 0 else "❌ Немає вільного"
            response_parts.append(
                f"  ➡️ <b>Вільний залишок:</b> <code>{free_stock:.2f}</code> ({free_stock_status})\n\n") # Использование HTML

            if len(remains_for_product) > 1:
                response_parts.append("<b>Деталі по партіях:</b>\n") # Использование HTML

            for r in remains_for_product:
                if r['line_of_business'] in ['Власне виробництво насіння', 'Насіння']:
                    response_parts.append(
                        f"  - Партія: <code>{r['nomenclature_series']}</code>\n" # Использование HTML
                        f"  - МТН: <code>{r['mtn']}</code>\n" # Использование HTML
                        f"  - Страна походження: <code>{r['origin_country']}</code>\n" # Использование HTML
                        f"  - Схожість: <code>{r['germination']}</code>\n" # Использование HTML
                        f"  - Рік урожаю: <code>{r['crop_year']}</code>\n" # Использование HTML
                        f"  - Вага: <code>{r['weight']}</code>\n" # Использование HTML
                        f"  - Наявність (Бух.): <code>{r['buh']}</code>\n" # Использование HTML
                        f"  - Наявність (Склад): <code>{r['skl']}</code>\n\n" # Использование HTML
                    )
                else:
                    response_parts.append(
                        f"  - Партія: <code>{r['nomenclature_series']}</code>\n" # Использование HTML
                        f"  - Наявність (Бух.): <code>{r['buh']}</code>\n" # Использование HTML
                        f"  - Наявність (Склад): <code>{r['skl']}</code>\n\n" # Использование HTML
                    )
        else:
            response_parts.append(f"📦 <b>Продукт: {product_entry[0]['product']}</b>\n") # Использование HTML
            response_parts.append("  <i>Залишків не знайдено.</i>") # Использование HTML

        final_response = "".join(response_parts)

        builder = InlineKeyboardBuilder()
        await state.update_data(current_product_uuid=product_uuid)
        builder.button(
            text="👉 Показати у кого під заявками",
            callback_data="show_submissions_for_last_viewed_product"
        )

        if len(final_response) > 4096: # Макс. длина сообщения в HTML
            await callback_query.message.answer(
                "📦 <b>Режим пошуку залишків</b>\nЗнайдено забагато результатів. Будь ласка, уточніть запит.",
                parse_mode=ParseMode.HTML)
        else:
            await callback_query.message.answer(
                final_response,
                reply_markup=builder.as_markup(),
                parse_mode=ParseMode.HTML
            )
        await state.set_state(BotStates.waiting_for_nomenclature) # Возвращаемся в режим поиска номенклатуры

    except Exception as e:
        logger.error(f"Error processing remains selection for user {callback_query.from_user.id}: {e}", exc_info=True)
        await callback_query.message.answer(
            f"📦 <b>Режим пошуку залишків</b>\nСталася помилка під час пошуку залишків. Спробуйте ще раз. Помилка: <code>{e}</code>",
            parse_mode=ParseMode.HTML)
        await state.set_state(BotStates.waiting_for_nomenclature) # Гарантируем возврат состояния
    finally:
        pass


@router.callback_query(
    lambda c: c.data and c.data.startswith('select_product_submissions:'))
async def process_submissions_product_selection(
        callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор продукта из инлайн-клавиатуры для заявок."""
    logger.info(f"User {callback_query.from_user.id} selected product for submissions: {callback_query.data}")
    await callback_query.answer()
    product_uuid = callback_query.data.split(':')[1]

    await callback_query.message.answer("📄 <b>Режим пошуку заявок</b>\nОбрано. Шукаю заявки...",
                                        parse_mode=ParseMode.HTML)

    try:
        product_entry = await get_product_by_id(product_uuid)
        if not product_entry:
            await callback_query.message.answer(
                "📄 <b>Режим пошуку заявок</b>\nПродукт не знайдено в довіднику.",
                parse_mode=ParseMode.HTML)
            await state.set_state(BotStates.waiting_for_submissions_nomenclature) # Возвращаемся
            return

        submissions_data = await get_submissions(product_entry[0]['id'])

        response_parts = []
        if submissions_data:
            response_parts.append(
                f"📄 <b>Заявки для продукту: {product_entry[0]['product']}</b>\n") # Использование HTML

            for s in submissions_data:
                response_parts.append(
                    f"  - Контрагент: <code>{s['client']}</code>\n" # Использование HTML
                    f"  - Менеджер: <code>{s['manager']}</code>\n" # Использование HTML
                    f"  - Доповнення: <code>{s['contract_supplement']}</code>\n" # Использование HTML
                    f"  - Кількість: <code>{s['different']}</code>\n\n" # Использование HTML
                )
        else:
            response_parts.append(
                f"📄 <b>Продукт: {product_entry[0]['product']}</b>\n") # Использование HTML
            response_parts.append("  <i>Заявок не знайдено.</i>\n") # Использование HTML

        final_response = "".join(response_parts)

        if len(final_response) > 4096: # Макс. длина сообщения в HTML
            await callback_query.message.answer(
                "📄 <b>Режим пошуку заявок</b>\nЗнайдено забагато результатів. Будь ласка, уточніть запит.",
                parse_mode=ParseMode.HTML)
        else:
            await callback_query.message.answer(final_response, parse_mode=ParseMode.HTML)

        await state.set_state(BotStates.waiting_for_submissions_nomenclature) # Возвращаемся в режим ввода номенклатуры

    except Exception as e:
        logger.error(f"Error processing submissions selection for user {callback_query.from_user.id}: {e}", exc_info=True)
        error_message = f"📄 <b>Режим пошуку заявок</b>\nСталася помилка під час пошуку заявок. Спробуйте ще раз. Помилка: <code>{e}</code>"
        await callback_query.message.answer(error_message, parse_mode=ParseMode.HTML)
        await state.set_state(BotStates.waiting_for_submissions_nomenclature)


@router.callback_query(
    lambda c: c.data == 'show_submissions_for_last_viewed_product')
async def show_submissions_for_product(callback_query: types.CallbackQuery,
                                       state: FSMContext):
    """
    Обрабатывает нажатие кнопки "Показать у кого под заявками" из сообщения с остатками.
    Получает UUID продукта из FSMContext и показывает заявки.
    """
    logger.info(f"User {callback_query.from_user.id} requested submissions for last viewed product.")
    await callback_query.answer("Завантажую заявки...")

    data = await state.get_data()
    product_uuid = data.get('current_product_uuid')

    if not product_uuid:
        await callback_query.message.answer(
            "📦 <b>Режим пошуку залишків</b>\nОшибка: Не удалось найти информацию о товаре. Пожалуйста, начните поиск остатков заново.",
            parse_mode=ParseMode.HTML)
        await state.set_state(BotStates.waiting_for_nomenclature) # Возвращаемся в режим
        return

    await callback_query.message.answer("📄 <b>Режим пошуку заявок</b>\nОбрано. Завантажую заявки...",
                                        parse_mode=ParseMode.HTML)

    try:
        product_entry = await get_product_by_id(product_uuid)
        if not product_entry:
            await callback_query.message.answer(
                "📄 <b>Режим пошуку заявок</b>\nПродукт не знайдено в довіднику.",
                parse_mode=ParseMode.HTML)
            await state.set_state(BotStates.waiting_for_nomenclature) # Возвращаемся в режим
            return

        submissions_data = await get_submissions(product_entry[0]['id'])

        response_parts = []
        if submissions_data:
            response_parts.append(
                f"📄 <b>Заявки для продукту: {product_entry[0]['product']}</b>\n") # Использование HTML

            for s in submissions_data:
                response_parts.append(
                    f"  - Контрагент: <code>{s['client']}</code>\n" # Использование HTML
                    f"  - Менеджер: <code>{s['manager']}</code>\n" # Использование HTML
                    f"  - Доповнення: <code>{s['contract_supplement']}</code>\n" # Использование HTML
                    f"  - Кількість: <code>{s['different']}</code>\n\n" # Использование HTML
                )
        else:
            response_parts.append(
                f"📄 <b>Продукт: {product_entry[0]['product']}</b>\n") # Использование HTML
            response_parts.append("  <i>Заявок не знайдено.</i>\n") # Использование HTML

        final_response = "".join(response_parts)

        if len(final_response) > 4096: # Макс. длина сообщения в HTML
            await callback_query.message.answer(
                "📄 <b>Режим пошуку заявок</b>\nЗнайдено забагато результатів. Будь ласка, уточніть запит.",
                parse_mode=ParseMode.HTML)
        else:
            await callback_query.message.answer(final_response, parse_mode=ParseMode.HTML)

        await state.set_state(BotStates.waiting_for_nomenclature) # Возвращаемся в режим поиска остатков

    except Exception as e:
        logger.error(f"Error showing submissions for last viewed product for user {callback_query.from_user.id}: {e}", exc_info=True)
        await callback_query.message.answer(
            f"📄 <b>Режим пошуку заявок</b>\nСталася помилка під час пошуку заявок. Спробуйте ще раз. Помилка: <code>{e}</code>",
            parse_mode=ParseMode.HTML)
        await state.set_state(BotStates.waiting_for_nomenclature) # Гарантируем возврат состояния
    finally:
        pass


# --- БЛОК 4: ОБЩИЕ ОБРАБОТЧИКИ СООБЩЕНИЙ (Fallback) ---
# Этот хендлер должен быть ПОСЛЕДНИМ среди всех @router.message() хендлеров,
# так как он срабатывает только если никакие другие хендлеры не обработали сообщение.

@router.message(StateFilter(None)) # Этот хендлер сработает только если нет активного FSM-состояния
async def echo_message(message: types.Message):
    """Обрабатывает сообщения, когда бот не находится ни в одном FSM-состоянии."""
    if message.text:
        await message.answer(
            "Для отримання потрібної інформації, скористайтеся кнопкой ' ☰ ', вона ліворуч",
            parse_mode=ParseMode.HTML)
    else:
        await message.answer("Ви отримали сповіщення, але воно не містить тексту.")
