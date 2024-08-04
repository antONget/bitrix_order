from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database.requests as rq
import logging


async def keyboard_select_status_order(tg_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора заказов с определенным статусом
    :return:
    """
    button_1 = InlineKeyboardButton(text=f'Новые заказы ({len(await rq.get_orders_status(rq.OrderStatus.new))})',
                                    callback_data='user_order_status_new')
    button_2 = InlineKeyboardButton(
        text=f'В работе ({len(await rq.get_order_idtg_and_status(tg_id=tg_id, status=rq.OrderStatus.work))})',
        callback_data='user_order_status_work')
    button_3 = InlineKeyboardButton(
        text=f'Выполненные ({len(await rq.get_order_idtg_and_status(tg_id=tg_id, status=rq.OrderStatus.complete))})',
        callback_data='user_order_status_complete')
    button_4 = InlineKeyboardButton(
        text=f'Невостребованные ({len(await rq.get_order_idtg_and_status(tg_id=tg_id, status=rq.OrderStatus.unclaimed))})',
        callback_data='user_order_status_unclaimed')
    button_5 = InlineKeyboardButton(
        text=f'Отмененные ({len(await rq.get_order_idtg_and_status(tg_id=tg_id, status=rq.OrderStatus.cancel))})',
        callback_data='user_order_status_cancel')
    button_6 = InlineKeyboardButton(
        text=f'Поиск заказа',
        callback_data='user_order_find')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button_1], [button_2], [button_3], [button_4], [button_5],
                                                     [button_6]])
    return keyboard


def keyboards_order_item(list_orders: list, block: int, status_order: str):
    """
    Клавиатура для вывода карточек заказа
    :param list_orders:
    :param block:
    :param status_order:
    :return:
    """
    logging.info(f"keyboards_order_item {len(list_orders)}, {block}")
    kb_builder = InlineKeyboardBuilder()
    buttons = []
    if status_order == 'new':
        text = f'Взять заказ {list_orders[block].id}'
        button = f'set_work_{list_orders[block].id}'
        buttons.append(InlineKeyboardButton(
            text=text,
            callback_data=button))
    elif status_order == 'work':
        text = f'Изменить статус'
        button = f'change_status_{list_orders[block].id}'
        buttons.append(InlineKeyboardButton(
            text=text,
            callback_data=button))
        text = f'Добавить информацию'
        button = f'add_detail_{list_orders[block].id}'
        buttons.append(InlineKeyboardButton(
            text=text,
            callback_data=button))
    if status_order != 'new':
        text = f'Подробнее'
        button = f'user_detail_order_{list_orders[block].id}'
        buttons.append(InlineKeyboardButton(
            text=text,
            callback_data=button))
    button_back = InlineKeyboardButton(text='<<',
                                       callback_data=f'user_order_back_{str(block)}')
    button_next = InlineKeyboardButton(text='>>',
                                       callback_data=f'user_order_forward_{str(block)}')
    kb_builder.row(*buttons, width=1)
    kb_builder.row(button_back, button_next)
    return kb_builder.as_markup()


def keyboard_back_item() -> InlineKeyboardMarkup:
    """
    Клавиатура возврата к списку заказов
    :return:
    """
    button_1 = InlineKeyboardButton(text=f'Назад',
                                    callback_data='back_order')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button_1]])
    return keyboard


def keyboard_change_status() -> InlineKeyboardMarkup:
    """
    Клавиатура изменения статуса
    :return:
    """
    button_1 = InlineKeyboardButton(text=f'Отказаться от заказ',
                                    callback_data='set_status_cancel')
    button_2 = InlineKeyboardButton(text=f'Заказ завершен',
                                    callback_data='set_status_complete')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button_1], [button_2]])
    return keyboard


def keyboard_continue_detail() -> InlineKeyboardMarkup:
    """
    Клавиатура изменения статуса
    :return:
    """
    button_1 = InlineKeyboardButton(text=f'Добавить еще',
                                    callback_data='add_more')
    button_2 = InlineKeyboardButton(text=f'Завершить',
                                    callback_data='add_not_more')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button_1], [button_2]])
    return keyboard
