import database.requests as rq
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from config_data.config import Config, load_config

config: Config = load_config()


async def process_unclaimed_order(bot: Bot):
    orders = await rq.get_orders_status(status=rq.OrderStatus.new)
    time_now = datetime.today() - timedelta(hours=12)
    for order in orders:
        date_create_order = order.data_create
        # '%H/%M/%S/%d/%m/%Y'
        create = datetime(int(date_create_order.split('/')[-1]),
                          int(date_create_order.split('/')[-2]),
                          int(date_create_order.split('/')[-3]),
                          int(date_create_order.split('/')[0]),
                          int(date_create_order.split('/')[1]),
                          int(date_create_order.split('/')[2]))
        if time_now > create:
            await rq.set_order_status(id_order=order.id, status=rq.OrderStatus.unclaimed)
            dispatchers = await rq.get_users_role(role=rq.UserRole.dispatcher)
            if dispatchers:
                for dispatcher in dispatchers:
                    try:
                        await bot.send_message(chat_id=dispatcher.tg_id,
                                               text=f'Заказ № {order.id_bitrix} переведен в статус не востребован')
                    except TelegramBadRequest:
                        pass
            for admin in config.tg_bot.admin_ids.split(','):
                try:
                    await bot.send_message(chat_id=int(admin),
                                           text=f'Заказ № {order.id_bitrix} переведен в статус не востребован')
                except TelegramBadRequest:
                    pass




