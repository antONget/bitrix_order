from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state


from config_data.config import Config, load_config
import database.requests as rq
import keyboards.keyboard_main as kb
from filter.admin_filter import check_personal

from faker import Faker
from datetime import datetime
import logging
import random

router = Router()
config: Config = load_config()


class Task(StatesGroup):
    id_task = State()


@router.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext) -> None:
    """
    Запуск бота - нажата кнопка "Начать" или введена команда "/start"
    Разграничиваем персонал и пользователей
    :param message:
    :return:
    """
    logging.info("process_start_command")
    await state.set_state(default_state)
    data = {"tg_id": message.chat.id, "username": message.from_user.username}
    if str(message.chat.id) in config.tg_bot.admin_ids.split(','):
        data = {"tg_id": message.chat.id, "username": message.from_user.username, "role": rq.UserRole.admin}
    await rq.add_user(data=data)
    if await check_personal(tg_id=message.chat.id):
        await message.answer(text=f'Приветственное сообщение',
                             reply_markup=kb.keyboards_main())
    else:
        await message.answer(text=f'Приветственное сообщение',
                             reply_markup=kb.keyboards_main_user())


@router.message(F.text == 'Разместить заказ')
async def add_task(message: Message, state: FSMContext) -> None:
    """
    Функция добавления заказа в БД телеграм бота
    :param message:
    :param state:
    :return:
    """
    logging.info(f'add_task {message.chat.id}')
    if await check_personal(tg_id=message.chat.id, role=rq.UserRole.dispatcher):
        await message.answer(text='Отправьте номер заказа из Bitrix для отправки ее мастерам.')
        await state.set_state(Task.id_task)
    else:
        await message.answer(text=f'У вас недостаточно прав для работы с этим функционалом.'
                                  f' Обратитесь к администратору.')


@router.message(StateFilter(Task.id_task), lambda message: message.text.isdigit())
async def add_task(message: Message, state: FSMContext) -> None:
    """
    Получаем номер заказа в CRM Bitrix для получения информация о заказе и клиенте
    :param message:
    :param state:
    :return:
    """
    logging.info(f'add_task {message.chat.id}')
    id_bitrix = int(message.text)
    fake = Faker()
    name = fake.name()
    address = fake.address()
    phone = fake.phone_number()
    order_detail = fake.text()
    amount = random.randint(100, 10000)
    await message.answer(text=f'<b>Клиент:</b>\n'
                              f'<i>Имя:</i> {name}\n'
                              f'<i>Адрес:</i> {address}\n'
                              f'<i>Телефон: {phone}</i>\n\n'
                              f'<b>Заказ: {message.text}</b>\n'
                              f'<i>Информация:</i> {order_detail}\n\n'
                              f'<b>Стоимость:</b> {amount}\n',
                         parse_mode='html')
    client_info_list = [name, address, phone]
    data = {"id_bitrix": id_bitrix,
            "status": rq.OrderStatus.new,
            "data_create": datetime.today().strftime('%H/%M/%S/%d/%m/%Y'),
            "tg_create": message.chat.id,
            "client_info": ','.join(client_info_list),
            "task_info": order_detail,
            "amount": amount}
    await rq.add_order(data=data)
    await message.answer(text=f'Заказ успешно добавлен в БД')
    await state.set_state(default_state)


@router.message(StateFilter(Task.id_task))
async def get_id_bitrix_error(message: Message, state: FSMContext):
    """
    Ошибка при вводе номера заказ
    :param message:
    :return:
    """
    logging.info(f'get_id_bitrix_error')
    await message.answer(text='Введите целое число.')
    await state.set_state(default_state)
