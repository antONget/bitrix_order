import database.requests as rq
from datetime import datetime, date, timedelta


async def process_unclaimed_order():
    orders = await rq.get_orders_status(status=rq.OrderStatus.new)
    time_now = datetime.today() - timedelta(minutes=10)
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
            print(f'Заказ {order.id} не востребован')
            await rq.set_order_status(id_order=order.id, status=rq.OrderStatus.unclaimed)
        else:
            print(f'Для заказа {order.id} время еще не вышло')



