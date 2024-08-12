from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import logging


def keyboards_main() -> ReplyKeyboardMarkup:
    """
    Главная административное меню
    :return:
    """
    logging.info("keyboards_main")
    button_1 = KeyboardButton(text='✅ Разместить заказ ✅')
    button_2 = KeyboardButton(text='💼 Меню заказов 💼')
    button_3 = KeyboardButton(text='📄 Отчеты 📄')
    button_4 = KeyboardButton(text='👨‍💼 Персонал 👨‍💼')
    keyboard = ReplyKeyboardMarkup(keyboard=[[button_1], [button_2], [button_3], [button_4]],
                                   resize_keyboard=True)
    return keyboard


def keyboards_main_personal() -> ReplyKeyboardMarkup:
    """
    Главная административное меню
    :return:
    """
    logging.info("keyboards_main")
    button_1 = KeyboardButton(text='✅ Разместить заказ ✅')
    button_2 = KeyboardButton(text='💼 Меню заказов 💼')
    keyboard = ReplyKeyboardMarkup(keyboard=[[button_1], [button_2]],
                                   resize_keyboard=True)
    return keyboard


def keyboards_main_user() -> ReplyKeyboardMarkup:
    """
    Главная административное меню
    :return:
    """
    logging.info("keyboards_main")
    button_1 = KeyboardButton(text='Мои заказы')
    button_2 = KeyboardButton(text='Баланс')
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[button_1], [button_2]],
        resize_keyboard=True
    )
    return keyboard


def keyboard_confirm_add_order() -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения добавления заказ
    :return:
    """
    logging.info("keyboard_confirm_add_order")
    button_1 = InlineKeyboardButton(text='Отмена',
                                    callback_data='add_order_cancel')
    button_2 = InlineKeyboardButton(text='Добавить заказ',
                                    callback_data='add_order_confirm')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button_1], [button_2]])
    return keyboard
