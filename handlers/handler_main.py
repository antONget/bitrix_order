from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state


from config_data.config import Config, load_config
import database.requests as rq
import keyboards.keyboard_main as kb
from filter.admin_filter import check_personal, check_super_admin
from bitrix import get_data_deal

from faker import Faker
from datetime import datetime
import logging
import random

router = Router()
config: Config = load_config()


class Task(StatesGroup):
    id_task = State()
    token = State()


@router.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext) -> None:
    """
    Запуск бота - нажата кнопка "Начать" или введена команда "/start"
    Разграничиваем персонал и пользователей (если пользователя нет в базе то заправшиваем у него токен)
    :param message:
    :param state:
    :return:
    """
    logging.info(f"process_start_command {message.chat.id}")
    await state.set_state(default_state)
    # администратор
    if check_super_admin(telegram_id=message.chat.id):
        data = {"token": "admin", "tg_id": message.chat.id, "username": message.from_user.username,
                "role": rq.UserRole.admin}
        await rq.add_admin(data=data)
    # есть ли пользователь в таблице
    if await rq.get_user_tg_id(tg_id=message.chat.id):
        # относится к персоналу
        if await check_personal(tg_id=message.chat.id):
            await message.answer(text=f'Приветственное сообщение',
                                 reply_markup=kb.keyboards_main())
        # или пользователю
        else:
            await message.answer(text=f'Приветственное сообщение',
                                 reply_markup=kb.keyboards_main_user())
    else:
        await message.answer(text='Для доступа к боту пришлите токен.')
        await state.set_state(Task.token)


@router.message(StateFilter(Task.token))
async def get_token(message: Message, bot: Bot, state: FSMContext):
    """
    Получение токена от пользователя и проверка его в базе
    :param message:
    :param bot:
    :param state:
    :return:
    """
    user = await rq.get_user_token(token=message.text)
    if user and not user.tg_id:
        data = {"token": message.text, "tg_id": message.chat.id, "username": message.from_user.username}
        await rq.set_add_user(data=data)
        await message.answer(text=f'Приветственное сообщение',
                             reply_markup=kb.keyboards_main_user())
        list_admin = config.tg_bot.admin_ids.split(',')
        for admin in list_admin:
            try:
                await bot.send_message(chat_id=int(admin),
                                       text=f'Пользователь {message.from_user.username} успешно авторизовался в боте')
            except IndexError:
                pass
        await state.set_state(default_state)
    else:
        await message.answer(text='TOKEN на прошел верификацию')


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


# @router.message(StateFilter(Task.id_task), lambda message: message.text.isdigit())
# async def add_task(message: Message, state: FSMContext) -> None:
#     """
#     Получаем номер заказа в CRM Bitrix для получения информация о заказе и клиенте
#     :param message:
#     :param state:
#     :return:
#     """
#     logging.info(f'add_task {message.chat.id}')
#     id_bitrix = int(message.text)
#     fake = Faker()
#     name = fake.name()
#     address = fake.address()
#     phone = fake.phone_number()
#     order_detail = fake.text()
#     amount = random.randint(100, 10000)
#     await message.answer(text=f'<b>Клиент:</b>\n'
#                               f'<i>Имя:</i> {name}\n'
#                               f'<i>Адрес:</i> {address}\n'
#                               f'<i>Телефон: {phone}</i>\n\n'
#                               f'<b>Заказ: {message.text}</b>\n'
#                               f'<i>Информация:</i> {order_detail}\n\n'
#                               f'<b>Стоимость:</b> {amount}\n',
#                          parse_mode='html')
#     client_info_list = [name, address, phone]
#     data = {"id_bitrix": id_bitrix,
#             "status": rq.OrderStatus.new,
#             "data_create": datetime.today().strftime('%H/%M/%S/%d/%m/%Y'),
#             "tg_create": message.chat.id,
#             "client_info": ','.join(client_info_list),
#             "task_info": order_detail,
#             "amount": amount}
#     await rq.add_order(data=data)
#     await message.answer(text=f'Заказ успешно добавлен в БД')
#     await state.set_state(default_state)


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
    if await rq.get_order_bitrix_id(bitrix_id=id_bitrix):
        await message.answer('Заказ с таким ID уже добавлен в базу данных')
        await state.set_state(default_state)
        # return
    await message.answer(text='Запрос отправлен в bitrix...')
    order_dict: dict = await get_data_deal(id_deal=id_bitrix)
    if not order_dict:
        await message.answer(text='Такой заказ не найден!')
        await state.set_state(default_state)
        return
    data = {"id_bitrix": id_bitrix,
            "status": rq.OrderStatus.new,
            "data_create": datetime.today().strftime('%H/%M/%S/%d/%m/%Y'),
            "tg_create": message.chat.id,
            "client_name": order_dict['Имя']['NAME'],
            "client_second_name": order_dict['Фамилия']['SECOND_NAME'],
            "client_last_name": order_dict['Отчество']['LAST_NAME'],
            "client_phone": order_dict["Телефон"]["PHONE"],
            "task_type_work": order_dict["Тип работы"]["UF_CRM_1722889585844"],
            "task_detail": order_dict["Детали работы:"]["UF_CRM_1722889647213"],
            "task_saratov": order_dict["Саратов"]["UF_CRM_1722889776466"],
            "task_engels": order_dict["Энгельс"]["UF_CRM_1722889900952"],
            "task_street": order_dict["Улица"]["UF_CRM_1722889043533"],
            "task_pay": order_dict["Оплата"]["UF_CRM_1722890070498"],
            "task_begin": order_dict["Начало работ "]["UF_CRM_1722890021769"]}
    print(data)
    await rq.add_order(data=data)
    order = await rq.get_order_bitrix_id(bitrix_id=id_bitrix)
    name = ''
    for n in [order.client_second_name, order.client_name, order.client_last_name]:
        if n != 'None':
            name += f'{n} '
    address = ''
    if order.task_saratov != 'None':
        if 'город' not in order.task_saratov:
            address += f'Саратов, {order.task_saratov}, {order.task_street}'
        else:
            address += f'Саратов, {order.task_street}'
    if order.task_engels != 'None':
        if 'город' not in order.task_engels:
            address += f'Энгельс, {order.task_engels}, {order.task_street}'
        else:
            address += f'Энгельс, {order.task_street}'
    await message.answer(text=f'<b>Заказ № {order.id_bitrix}</b>\n\n'
                              f'<b>Клиент:</b>\n'
                              f'<i>Имя:</i> {name}\n'
                              f'<i>Телефон: {order.client_phone}</i>\n'
                              f'<i>Адрес:</i> {address}\n\n'
                              f'<b>Заказ: {message.text}</b>\n'
                              f'<i>Тип работы:</i> {order.task_type_work}\n'
                              f'<i>Детали работы:</i> {order.task_detail}\n'
                              f'<i>Оплата:</i> {order.task_pay}\n'
                              f'<i>Начало работ:</i> {order.task_begin}\n',
                         parse_mode='html')
    await message.answer(text=f'Заказ успешно добавлен в БД')
    await state.set_state(default_state)


@router.message(StateFilter(Task.id_task))
async def get_id_bitrix_error(message: Message, state: FSMContext):
    """
    Ошибка при вводе номера заказ
    :param message:
    :param state:
    :return:
    """
    logging.info(f'get_id_bitrix_error {message.chat.id}')
    await message.answer(text='Введите целое число.')
    await state.set_state(default_state)
