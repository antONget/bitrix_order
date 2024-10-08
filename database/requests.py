from database.models import User, Order
from database.models import async_session
from sqlalchemy import select
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class UserRole:
    user = "user"
    admin = "admin"
    dispatcher = "dispatcher"
    manager = "manager"
    personal = "personal"


async def add_admin(data: dict):
    """
    Добавляем нового пользователя если его еще нет в БД
    :param data:
    :return:
    """
    logging.info(f'add_admin')
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == int(data["tg_id"])))
        if not user:
            session.add(User(**data))
            await session.commit()


async def set_add_user(data: dict):
    """
    Добавляем нового пользователя если его еще нет в БД
    :param data:
    :return:
    """
    logging.info(f'set_add_user')
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == int(data["tg_id"])))
        if not user:
            token = await session.scalar(select(User).where(User.token == data["token"]))
            if token:
                token.tg_id = data["tg_id"]
                token.username = data["username"]
                await session.commit()


async def add_token(data: dict):
    """
    Добавляем токен
    :param data:
    :return:
    """
    logging.info(f'add_token')
    async with async_session() as session:
        session.add(User(**data))
        await session.commit()


async def get_all_users() -> list[User]:
    """
    Получаем список всех пользователей зарегистрированных в боте
    :return:
    """
    logging.info(f'get_all_users')
    async with async_session() as session:
        users = await session.scalars(select(User))
        return users


async def get_users_role(role: str) -> list[User]:
    """
    Получаем список всех пользователей с определенной ролью
    :return:
    """
    logging.info(f'get_users_role')
    async with async_session() as session:
        if role == UserRole.manager:
            users = await session.scalars(select(User).where(User.is_manager == 1))
        elif role == UserRole.dispatcher:
            users = await session.scalars(select(User).where(User.is_dispatcher == 1))
        return users


async def get_users_role_not(role: str) -> list[User]:
    """
    Получаем список всех пользователей c определенной ролью
    role
    :return:
    """
    logging.info(f'get_users_role_not')
    async with async_session() as session:
        if role == UserRole.manager:
            users = await session.scalars(select(User).where(User.is_manager != 1, User.is_admin != UserRole.admin))
        elif role == UserRole.dispatcher:
            users = await session.scalars(select(User).where(User.is_dispatcher != 1, User.is_admin != UserRole.admin))
        return users


async def get_user_tg_id(tg_id: int) -> User:
    """
    Получаем информацию по пользователю
    :param tg_id:
    :return:
    """
    logging.info(f'get_user_tg_id')
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user


async def get_user_token(token: str):
    """
    Получаем информацию по пользователю
    :param token:
    :return:
    """
    logging.info(f'get_user_token')
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.token == token))
        return user


async def set_user_role(tg_id: int, role: str, change_role: str = UserRole.dispatcher):
    """
    Обновляем роль пользователя
    :param tg_id:
    :param role:
    :param change_role:
    :return:
    """
    logging.info(f'set_user_role: {role}')
    async with async_session() as session:
        user: User = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            if role == UserRole.dispatcher:
                user.is_dispatcher = 1
            elif role == UserRole.manager:
                user.is_manager = 1
            elif role == 'ban':
                user.is_manager = 1
            elif role == UserRole.user:
                if change_role == UserRole.dispatcher:
                    user.is_dispatcher = 0
                elif change_role == UserRole.manager:
                    user.is_manager = 0
            await session.commit()


@dataclass
class OrderStatus:
    new = "new"
    work = "work"
    cancel = "cancel"
    unclaimed = "unclaimed"
    complete = "complete"
    close = "close"


async def add_order(data: dict, id_bitrix: int):
    """
    Добавляем новый заказ
    :param data:
    :param id_bitrix:
    :return:
    """
    logging.info(f'add_order')
    async with async_session() as session:
        if not await session.scalar(select(Order).where(Order.id_bitrix == id_bitrix)):
            session.add(Order(**data))
            await session.commit()


async def get_orders_status(status: str) -> list[Order]:
    """
    Получаем список заказов с определенным статусом
    :param status: [new, complete, cancel, unclaimed]
    :return:
    """
    logging.info(f'get_users_role')
    async with async_session() as session:
        orders = await session.scalars(select(Order).where(Order.status == status))
        return orders.all()


async def get_order_id(id_order: int) -> Order:
    """
    Получаем заказ по его id
    :param id_order:
    :return:
    """
    logging.info(f'get_order_id')
    async with async_session() as session:
        order = await session.scalar(select(Order).where(Order.id == id_order))
        return order


async def get_order_bitrix_id(bitrix_id: int):
    """
    Получаем заказ по его ID в системе bitrix
    :param bitrix_id:
    :return:
    """
    logging.info(f'get_order_bitrix_id')
    async with async_session() as session:
        orders = await session.scalar(select(Order).where(Order.id_bitrix == bitrix_id))
        return orders


async def get_order_idtg_and_status(tg_id: int, status: str):
    """
    Получаем заказ по его id
    :param tg_id:
    :param status:
    :return:
    """
    logging.info(f'get_order_id')
    async with async_session() as session:
        order = await session.scalars(select(Order).where(Order.tg_executor == tg_id, Order.status == status))
        return order.all()


async def get_orders_all():
    """
    Получаем все заказы
    :return:
    """
    logging.info(f'get_orders_all')
    async with async_session() as session:
        order = await session.scalars(select(Order))
        return order


async def set_order_amount(id_order: int, amount: float):
    """
    Обновляем роль пользователя
    :param id_order:
    :param amount:
    :return:
    """
    logging.info(f'set_order_amount')
    async with async_session() as session:
        order: Order = await session.scalar(select(Order).where(Order.id == id_order))
        order.amount = amount
        await session.commit()


async def set_order_status(id_order: int, status: str):
    """
    Обновляем статус заказа, если возвращаем его из невостребованных то обновляем еще и дату создания
    :param id_order:
    :param status:
    :return:
    """
    logging.info(f'set_order_status')
    async with async_session() as session:
        order: Order = await session.scalar(select(Order).where(Order.id == id_order))
        if order:
            if status == OrderStatus.new:
                order.data_create = datetime.today().strftime('%H/%M/%S/%d/%m/%Y')
            order.status = status
            await session.commit()


async def set_order_reason_of_refusal(id_order: int, refusal: str):
    """
    Обновляем причину отказа
    :param id_order:
    :param refusal:
    :return:
    """
    logging.info(f'set_order_reason_of_refusal')
    async with async_session() as session:
        order: Order = await session.scalar(select(Order).where(Order.id == id_order))
        order.reason_of_refusal = refusal
        await session.commit()


async def set_order_detail_text(id_order: int, detail_text: str):
    """
    Обновляем тестовый материал добавляемый мастером
    :param id_order:
    :param detail_text:
    :return:
    """
    logging.info(f'set_order_reason_of_refusal')
    async with async_session() as session:
        order: Order = await session.scalar(select(Order).where(Order.id == id_order))
        order.order_detail_text = detail_text
        await session.commit()


async def set_order_detail_photo(id_order: int, detail_photo: str):
    """
    Обновляем фото материал добавляемый мастером
    :param id_order:
    :param detail_photo:
    :return:
    """
    logging.info(f'set_order_reason_of_refusal')
    async with async_session() as session:
        order: Order = await session.scalar(select(Order).where(Order.id == id_order))
        order.order_detail_photo = detail_photo
        await session.commit()


async def set_order_work(id_order: int, tg_executor: int, data_work: str):
    """
    Обновляем исполнителя заказа
    :param id_order:
    :param tg_executor:
    :param data_work:
    :return:
    """
    logging.info(f'set_order_executor')
    async with async_session() as session:
        order: Order = await session.scalar(select(Order).where(Order.id == id_order))
        order.tg_executor = tg_executor
        order.data_work = data_work
        order.status = OrderStatus.work
        await session.commit()
