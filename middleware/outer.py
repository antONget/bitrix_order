import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
import database.requests as rq


logger = logging.getLogger(__name__)


class FirstOuterMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:

        user: User = data.get('event_from_user')
        if user is not None:
            user_check = await rq.get_user_tg_id(tg_id=user.id)
            if user_check and user_check.is_ban:
                text = 'Вас забанили'
                try:
                    await event.answer(text=text)
                except:
                    await event.message.answer(text=text)
                return
        return await handler(event, data)
