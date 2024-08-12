from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.filters import StateFilter

import keyboards.keyboards_edit_list_personal as kb
import database.requests as rq
from filter.admin_filter import check_super_admin
from config_data.config import Config, load_config
from secrets import token_urlsafe
import asyncio
import logging

config: Config = load_config()
router = Router()


class Personal(StatesGroup):
    id_tg_personal = State()
    id_tg_ban = State()


# Персонал
@router.message(F.text == '👨‍💼 Персонал 👨‍💼', lambda message: check_super_admin(message.chat.id))
async def process_change_list_personal(message: Message) -> None:
    """
    Выбор роли для редактирования списка
    :param message:
    :return:
    """
    logging.info(f'process_change_list_personal: {message.chat.id}')
    await message.answer(text="Выберите роль которую вы хотите изменить.",
                         reply_markup=kb.keyboard_select_role())


@router.callback_query(F.data == 'add_user')
async def process_add_user(callback: CallbackQuery) -> None:
    logging.info(f'process_add_user: {callback.message.chat.id}')
    token = str(token_urlsafe(8))
    data = {"token": token}
    await rq.add_token(data=data)
    await callback.message.edit_text(text=f'Для добавления пользователя в бот отправьте ему этот TOKEN'
                                          f' <code>{token}</code>.'
                                          f' По этому TOKEN может быть добавлен только один пользователь,'
                                          f' не делитесь и не показывайте его никому, кроме тех лиц для кого он'
                                          f' предназначен',
                                     parse_mode='html')


# добавление администратора
@router.callback_query(F.data.startswith('edit_list_'))
async def process_select_action(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Выбор действия которое нужно совершить с ролью при редактировании
    :param callback:
    :param state:
    :return:
    """
    logging.info(f'process_add_admin: {callback.message.chat.id}')
    edit_role = callback.data.split('_')[2]
    role = 'менеджера'
    if edit_role == rq.UserRole.dispatcher:
        role = 'диспетчера'
    await state.update_data(edit_role=edit_role)
    await callback.message.edit_text(text=f"Добавить или удалить {role}?",
                                     reply_markup=kb.keyboard_select_action())
    await callback.answer()


@router.callback_query(F.data == 'personal_add')
async def process_personal_add(callback: CallbackQuery, state: FSMContext) -> None:
    logging.info(f'process_personal_add: {callback.message.chat.id}')
    data = await state.get_data()
    edit_role = data['edit_role']
    role = 'менеджером'
    if edit_role == 'dispatcher':
        role = 'диспетчером'
    await callback.message.answer(text=f'Пришлите id telegram пользователя для назначения его {role}.\n\n'
                                       f'Важно!!! Пользователь должен запустить бота.\n\n'
                                       f'Получить id telegram пользователя можно при помощи бота: '
                                       f'@getmyid_bot или @username_to_id_bot')
    await state.set_state(Personal.id_tg_personal)


@router.message(F.text, StateFilter(Personal.id_tg_personal))
async def get_id_tg_personal(message: Message, state: FSMContext):
    """
    Получаем id телегарам для добавления в список персонала
    :param message:
    :param state:
    :return:
    """
    tg_id_personal = int(message.text)
    data = await state.get_data()
    edit_role = data['edit_role']
    role = 'менеджеров'
    if edit_role == 'dispatcher':
        role = 'диспетчеров'
    await rq.set_user_role(tg_id=tg_id_personal, role=edit_role)
    user = await rq.get_user_tg_id(tg_id=tg_id_personal)
    if user:
        await message.answer(text=f'Пользователь @{user.username} добавлен в список {role}')
        await state.set_state(default_state)
    else:
        await message.answer(text=f'Пользователь c id={tg_id_personal} в базе данных не найден')
    await state.set_state(default_state)


@router.callback_query(F.data == 'ban_user')
async def process_personal_add(callback: CallbackQuery, state: FSMContext) -> None:
    logging.info(f'process_personal_add: {callback.message.chat.id}')
    await callback.message.answer(text=f'Пришлите id telegram пользователя для его блокировки в боте.\n\n'
                                       f'Получить id telegram пользователя можно при помощи бота: '
                                       f'@getmyid_bot или @username_to_id_bot')
    await state.set_state(Personal.id_tg_ban)


@router.message(F.text, StateFilter(Personal.id_tg_ban))
async def get_id_tg_personal(message: Message, state: FSMContext):
    """
    Получаем id телегарам для добавления в список бана
    :param message:
    :param state:
    :return:
    """
    tg_id_ban = int(message.text)
    await rq.set_user_role(tg_id=tg_id_ban, role='ban')
    user = await rq.get_user_tg_id(tg_id=tg_id_ban)
    if user:
        await message.answer(text=f'Пользователь @{user.username} заблокирован')
        await state.set_state(default_state)
    else:
        await message.answer(text=f'Пользователь c id={tg_id_ban} в базе данных не найден')
    await state.set_state(default_state)


# отмена добавления пользователя в список администраторов
@router.callback_query(F.data == 'not_add_personal_list')
async def process_not_add_admin_list(callback: CallbackQuery, bot: Bot) -> None:
    """
    Отмена назначение персонала
    :param callback:
    :param bot:
    :return:
    """
    logging.info(f'process_not_add_admin_list: {callback.message.chat.id}')
    await bot.delete_message(chat_id=callback.message.chat.id,
                             message_id=callback.message.message_id)
    await process_change_list_personal(callback.message)


# удаление после подтверждения
@router.callback_query(F.data == 'add_personal_list')
async def process_add_admin_list(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Подтверждение назначение персонала
    :param callback:
    :param state:
    :return:
    """
    logging.info(f'process_add_admin_list: {callback.message.chat.id}')
    await bot.delete_message(chat_id=callback.message.chat.id,
                             message_id=callback.message.message_id)
    data = await state.get_data()
    edit_role = data['edit_role']
    tg_id = data['add_personal']
    role = 'менеджером'
    if edit_role == rq.UserRole.dispatcher:
        role = 'диспетчером'
    await rq.set_user_role(tg_id=tg_id, role=edit_role)
    await callback.answer(text=f'Пользователь успешно назначен {role}', show_alert=True)
    await asyncio.sleep(1)
    await process_change_list_personal(callback.message)


# разжалование администратора
@router.callback_query(F.data == 'personal_delete')
async def process_del_admin(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Выбор пользователя для разжалования его из персонала
    :param callback:
    :param state:
    :return:
    """
    logging.info(f'process_del_admin: {callback.message.chat.id}')
    data = await state.get_data()
    edit_role = data['edit_role']
    role = 'менеджеров'
    if edit_role == 'dispatcher':
        role = 'диспетчеров'
    list_users = await rq.get_users_role(role=edit_role)
    list_personal = []
    for user in list_users:
        list_personal.append([user.tg_id, user.username])
    keyboard = kb.keyboards_del_admin(list_personal, 0, 2, 6)
    await callback.message.edit_text(text=f'Выберите пользователя, которого нужно удалить из {role}',
                                     reply_markup=keyboard)
    await callback.answer()


# >>>>
@router.callback_query(F.data.startswith('admin_del_forward'))
async def process_forward_del_admin(callback: CallbackQuery, state: FSMContext) -> None:
    logging.info(f'process_forward_del_admin: {callback.message.chat.id}')
    data = await state.get_data()
    edit_role = data['edit_role']
    role = 'менеджеров'
    if edit_role == 'dispatcher':
        role = 'диспетчеров'
    list_users = await rq.get_users_role(role=edit_role)
    list_personal = []
    for user in list_users:
        list_personal.append([user.tg_id, user.username])
    forward = int(callback.data.split('_')[3]) + 1
    back = forward - 2
    keyboard = kb.keyboards_del_admin(list_personal, back, forward, 2)
    try:
        await callback.message.edit_text(text=f'Выберите пользователя, которого вы хотите удалить из {role}',
                                         reply_markup=keyboard)
    except TelegramBadRequest:
        await callback.message.edit_text(text=f'Выберитe пользоватeля, которого вы хотите удалить из {role}',
                                         reply_markup=keyboard)


# <<<<
@router.callback_query(F.data.startswith('admin_del_back'))
async def process_back_del_admin(callback: CallbackQuery, state: FSMContext) -> None:
    logging.info(f'process_back_del_admin: {callback.message.chat.id}')
    data = await state.get_data()
    edit_role = data['edit_role']
    role = 'менеджеров'
    if edit_role == 'dispatcher':
        role = 'диспетчеров'
    list_users = await rq.get_users_role(role=edit_role)
    list_personal = []
    for user in list_users:
        list_personal.append([user.tg_id, user.username])
    back = int(callback.data.split('_')[3]) - 1
    forward = back + 2
    keyboard = kb.keyboards_del_admin(list_personal, back, forward, 2)
    try:
        await callback.message.edit_text(text=f'Выберите пользователя, которого вы хотите удалить из {role}',
                                         reply_markup=keyboard)
    except TelegramBadRequest:
        await callback.message.edit_text(text=f'Выберитe пользоватeля, которого вы хотите удалить из {role}',
                                         reply_markup=keyboard)


# подтверждение добавления админа в список
@router.callback_query(F.data.startswith('admin_del'))
async def process_delete_user(callback: CallbackQuery, state: FSMContext) -> None:
    logging.info(f'process_delete_user: {callback.message.chat.id}')
    data = await state.get_data()
    edit_role = data['edit_role']
    role = 'менеджеров'
    if edit_role == rq.UserRole.dispatcher:
        role = 'диспетчеров'
    telegram_id = int(callback.data.split('_')[2])
    user_info = await rq.get_user_tg_id(tg_id=telegram_id)
    await state.update_data(del_personal=telegram_id)
    await callback.message.edit_text(text=f'Удалить пользователя {user_info.username} из {role}',
                                     reply_markup=kb.keyboard_del_list_admins())


# отмена удаления пользователя в список администраторов
@router.callback_query(F.data == 'not_del_personal_list')
async def process_not_del_personal_list(callback: CallbackQuery, bot: Bot) -> None:
    """
    Отмена изменения роли пользователя
    :param callback:
    :return:
    """
    logging.info(f'process_not_del_personal_list: {callback.message.chat.id}')
    await bot.delete_message(chat_id=callback.message.chat.id,
                             message_id=callback.message.message_id)
    await process_change_list_personal(callback.message)


# удаление после подтверждения
@router.callback_query(F.data == 'del_personal_list')
async def process_del_personal_list(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    logging.info(f'process_del_personal_list: {callback.message.chat.id}')
    await bot.delete_message(chat_id=callback.message.chat.id,
                             message_id=callback.message.message_id)
    data = await state.get_data()
    tg_id = data['del_personal']
    edit_role = data['edit_role']
    role = 'менеджеров'
    if edit_role == 'dispatcher':
        role = 'диспетчеров'
    await rq.set_user_role(tg_id=tg_id, role=rq.UserRole.user, change_role=edit_role)
    await callback.answer(text=f'Пользователь успешно удален из {role}', show_alert=True)
    await asyncio.sleep(1)
    await process_change_list_personal(callback.message)
