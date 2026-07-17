from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any
import logging

# Получаем логгер для этой мидлвари
logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Any],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        user = event.from_user

        if isinstance(event, Message):
            log_message = f"[{user.full_name} ({user.id})] MESSAGE: {event.text}"
        elif isinstance(event, CallbackQuery):
            log_message = f"[{user.full_name} ({user.id})] CALLBACK: {event.data}"
        else:
            log_message = f"[{user.full_name} ({user.id})] UNKNOWN EVENT TYPE: {type(event).__name__}"

        logger.info(log_message)

        # Вызываем следующий обработчик в цепочке (это может быть другой мидлварь или сам хендлер)
        return await handler(event, data)