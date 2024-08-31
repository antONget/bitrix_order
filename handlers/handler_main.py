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
    # добавляем администратора
    if check_super_admin(telegram_id=message.chat.id):
        data = {"token": "admin", "tg_id": message.chat.id, "username": message.from_user.username, "is_admin": 1}
        await rq.add_admin(data=data)
    # есть ли пользователь в таблице
    if await rq.get_user_tg_id(tg_id=message.chat.id):
        # относится к администратору
        if check_super_admin(telegram_id=message.chat.id):
            await message.answer(text=f'Я бот MasterClass. Рад с вами работать. 👋',
                                 reply_markup=kb.keyboards_main())
        # относится к персоналу
        elif await check_personal(tg_id=message.chat.id):
            await message.answer(text=f'Я бот MasterClass. Рад с вами работать. 👋',
                                 reply_markup=kb.keyboards_main_personal())
        # или пользователю
        else:
            await message.answer(text=f'Я бот MasterClass. Рад с вами работать. 👋',
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
        if message.from_user.username:
            username = message.from_user.username
        else:
            username = 'None'
        data = {"token": message.text, "tg_id": message.chat.id, "username": username}
        await rq.set_add_user(data=data)
        await message.answer(text=f'Я бот MasterClass. Рад с вами работать. 👋',
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


@router.message(F.text == '✅ Разместить заказ ✅')
async def add_task(message: Message, state: FSMContext) -> None:
    """
    Функция добавления заказа в БД телеграм бота
    :param message:
    :param state:
    :return:
    """
    logging.info(f'add_task {message.chat.id}')
    if await check_personal(tg_id=message.chat.id, role=rq.UserRole.dispatcher):
        await message.answer(text='👉 Введите ID заказа:')
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
    try:
        id_bitrix = int(message.text)
    except:
        await message.answer(text='Введите целое число.')
        await state.set_state(default_state)
        return
    if await rq.get_order_bitrix_id(bitrix_id=id_bitrix):
        await message.answer('Заказ с таким ID уже добавлен в базу данных')
        await state.set_state(default_state)
        return
    await message.answer(text='Запрос отправлен в bitrix...')
    order_dict: dict = await get_data_deal(id_deal=id_bitrix)
    if order_dict == 'No_deal':
        await message.answer(text=f'Заказ {id_bitrix} не найден!')
        await state.set_state(default_state)
        return
    if order_dict == 'No_contact':
        await message.answer(text=f'К заказу № {id_bitrix} не добавлен контакт!')
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
            "task_detail": order_dict["Детали работы:"]["UF_CRM_1723401519885"],
            "task_saratov_area": order_dict["Саратовская область "]["UF_CRM_1723096401639"],
            "task_saratov": order_dict["Саратов"]["UF_CRM_1723401598955"],
            "task_engels": order_dict["Энгельс"]["UF_CRM_1722889900952"],
            "task_street": order_dict["Улица"]["UF_CRM_1722889043533"].split('|')[0],
            "task_pay": order_dict["Оплата"]["UF_CRM_1722890070498"],
            "task_begin": order_dict["Начало работ "]["UF_CRM_1722890021769"]}
    await rq.add_order(data=data, id_bitrix=id_bitrix)

    order = await rq.get_order_bitrix_id(bitrix_id=id_bitrix)
    name = ''
    for n in [order.client_second_name, order.client_name, order.client_last_name]:
        if n != 'None':
            name += f'{n} '
    address = ''
    if order.task_saratov != 'None':
        if 'город' not in order.task_saratov:
            address += f'Город: <b>{"Саратов"}</b>\n'
            if order.task_saratov:
                address += f'Район: <b>{order.task_saratov}</b>\n'
        else:
            address += f'Город: <b>{"Саратов"}</b>\n'
    elif order.task_engels != 'None':
        if 'город' not in order.task_engels:
            address += f'Город: <b>{"Энгельс"}</b>\n'
            if order.task_engels:
                address += f'Район: <b>{order.task_engels}</b>\n'
        else:
            address += f'Город: <b>{"Энгельс"}</b>\n'
    elif order.task_saratov_area != 'None':
        address += f'Саратовская область:\n' \
                        f'Район: <b>{order.task_saratov_area}</b>\n'
    if order.task_street:
        address += f'Улица: <b>{order.task_street.split("|")[0]}</b>\n\n'
    await message.answer(text=f'Заказ № <b>{order.id_bitrix}</b>\n\n'
                              f'<b>Клиент:</b>\n'
                              f'Имя: <b>{name}</b>\n'
                              f'Телефон: <code>{order.client_phone}</code>\n'
                              f'Адрес:\n'
                              f'{address}\n'
                              f'Тип работы: <b>{order.task_type_work}</b>\n'
                              f'Детали работы: <b>{order.task_detail}</b>\n'
                              f'Оплата: <b>{order.task_pay}</b>\n'
                              f'Начало работ: <b>{order.task_begin}</b>\n',
                         parse_mode='html')
    await message.answer(text=f'Заказ успешно добавлен в БД')
    await state.set_state(default_state)
