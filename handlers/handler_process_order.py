from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.filters import StateFilter
from aiogram.exceptions import TelegramBadRequest

import keyboards.keyboard_process_order as kb
import database.requests as rq
from filter.admin_filter import check_personal, IsPersonal
from config_data.config import Config, load_config


import logging

config: Config = load_config()
router = Router()
user_dict = {}


class OrderPersonal(StatesGroup):
    set_amount = State()
    set_comment = State()
    search_id = State()


# Персонал
@router.message(F.text == '💼 Меню заказов 💼', IsPersonal())
async def process_order_list(message: Message) -> None:
    """
    Выбор статуса заказа для его обработки
    :param message:
    :return:
    """
    logging.info(f'process_order_list: {message.chat.id}')
    if await check_personal(message.chat.id):
        await message.answer(text="Меню заказов:",
                             reply_markup=await kb.keyboard_select_status_order())
    else:
        await message.answer(text=f'У вас недостаточно прав для работы с этим функционалом.'
                                  f' Обратитесь к администратору.')


@router.callback_query(F.data.startswith('order_status_'))
async def show_merch_slider(callback: CallbackQuery, state: FSMContext):
    """
    Выводим карточки выбранным статусом в блоках
    :param callback:
    :param state:
    :return:
    """
    logging.info(f'show_merch_slider: {callback.message.chat.id}')
    status_order = callback.data.split('_')[2]
    # новые и завершенные заказы доступны всему персонал
    if status_order in [rq.OrderStatus.new, rq.OrderStatus.complete]:
        role = rq.UserRole.personal
    # отменные и невостребованные админу и диспетчеру
    elif status_order in [rq.OrderStatus.cancel, rq.OrderStatus.unclaimed]:
        role = rq.UserRole.dispatcher
    # в работе админу и менеджеру
    else:
        role = rq.UserRole.manager
    if await check_personal(tg_id=callback.message.chat.id, role=role):
        await state.update_data(status_order=status_order)
        list_orders = [order for order in await rq.get_orders_status(status=status_order)]
        count_block = len(list_orders)
        if count_block == 0:
            await callback.answer(text=f'В разделе нет заказов', show_alert=True)
            return
        # выводим карточки
        keyboard = kb.keyboards_order_item(list_orders=list_orders, block=0, status_order=status_order)

        order = list_orders[0]
        # Формируем имя клиента
        name = ''
        for n in [order.client_second_name, order.client_name, order.client_last_name]:
            if n != 'None':
                name += f'{n} '
        # Формируем адрес клиента
        address = ''
        if order.task_saratov != 'None':
            if 'город' not in order.task_saratov:
                address += f'Саратов, {order.task_saratov}, {order.task_street.split("|")[0]}'
            else:
                address += f'Саратов, {order.task_street}'
        if order.task_engels != 'None':
            if 'город' not in order.task_engels:
                address += f'Энгельс, {order.task_engels}, {order.task_street.split("|")[0]}'
            else:
                address += f'Энгельс, {order.task_street}'
        if order.task_saratov_area != 'None':
            address += f'Саратовская область, {order.task_saratov_area}, {order.task_street.split("|")[0]}'
        # Формируем карточку заказа
        message_text = ''
        status_order_text = ''
        if status_order == rq.OrderStatus.new:
            status_order_text = '🔔 Новый 🔔'
        elif status_order == rq.OrderStatus.cancel:
            status_order_text = '🚫 Отмененный 🚫'
        elif status_order == rq.OrderStatus.work:
            status_order_text = '🛠 В работе 🛠'
        elif status_order == rq.OrderStatus.complete:
            status_order_text = '✅ Выполненный ✅'
        elif status_order == rq.OrderStatus.unclaimed:
            status_order_text = '🔕 Невостребованный 🔕'
        message_text += f'<b>{status_order_text} заказ № {order.id_bitrix}</b>\n\n' \
                        f'<b>Клиент:</b>\n' \
                        f'<i>Имя:</i> {name}\n' \
                        f'<i>Телефон: {order.client_phone}</i>\n' \
                        f'<i>Адрес:</i> {address}\n\n' \
                        f'<b>Заявка</b>\n' \
                        f'<i>Тип работы:</i> {order.task_type_work}\n' \
                        f'<i>Детали работы:</i> {order.task_detail}\n\n'
        if status_order in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
            message_text += f'<i>Мастер:</i> @{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                            f'tg_id{order.tg_executor}\n'
        if status_order == rq.OrderStatus.cancel:
            message_text += f'<i>Причина отказа:</i> {order.reason_of_refusal}\n'
        await callback.message.answer(text=message_text,
                                      reply_markup=keyboard,
                                      parse_mode='html')
    else:
        await callback.answer(text=f'У вас недостаточно прав для работы с этим функционалом. '
                                   f'Обратитесь к администратору.', show_alert=True)


# >>
@router.callback_query(F.data.startswith('status_order_forward_'))
async def process_forward(callback: CallbackQuery, state: FSMContext):
    """
    Пагинация вперед
    :param callback: int(callback.data.split('_')[1]) номер блока для вывода
    :param state:
    :return:
    """
    logging.info(f'process_forward_game: {callback.message.chat.id}')
    data = await state.get_data()
    status_order = data['status_order']
    models_orders = await rq.get_orders_status(status=status_order)
    list_orders = []
    for order in models_orders:
        list_orders.append(order)
    count_block = len(list_orders)
    num_block = int(callback.data.split('_')[3]) + 1
    if num_block == count_block:
        num_block = 0
    keyboard = kb.keyboards_order_item(list_orders=list_orders, block=num_block, status_order=status_order)
    try:
        order = list_orders[num_block]
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
        if order.task_saratov_area != 'None':
            address += f'Саратовская область, {order.task_saratov_area}, {order.task_street}'
            # Формируем карточку заказа
            message_text = ''
            status_order_text = ''
            if status_order == rq.OrderStatus.new:
                status_order_text = '🔔 Новый 🔔'
            elif status_order == rq.OrderStatus.cancel:
                status_order_text = '🚫 Отмененный 🚫'
            elif status_order == rq.OrderStatus.work:
                status_order_text = '🛠 В работе 🛠'
            elif status_order == rq.OrderStatus.complete:
                status_order_text = '✅ Выполненный ✅'
            elif status_order == rq.OrderStatus.unclaimed:
                status_order_text = '🔕 Невостребованный 🔕'
            message_text += f'<b>{status_order_text} заказ № {order.id_bitrix}</b>\n\n' \
                            f'<b>Клиент:</b>\n' \
                            f'<i>Имя:</i> {name}\n' \
                            f'<i>Телефон: {order.client_phone}</i>\n' \
                            f'<i>Адрес:</i> {address}\n\n' \
                            f'<b>Заявка</b>\n' \
                            f'<i>Тип работы:</i> {order.task_type_work}\n' \
                            f'<i>Детали работы:</i> {order.task_detail}\n\n'
            if status_order in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
                message_text += f'<i>Мастер:</i> @{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                                f'tg_id{order.tg_executor}\n'
            if status_order == rq.OrderStatus.cancel:
                message_text += f'<i>Причина отказа:</i> {order.reason_of_refusal}\n'
            await callback.message.answer(text=message_text,
                                          reply_markup=keyboard,
                                          parse_mode='html')
    except TelegramBadRequest:
        order = list_orders[num_block]
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
        if order.task_saratov_area != 'None':
            address += f'Саратовская область, {order.task_saratov_area}, {order.task_street}'
            # Формируем карточку заказа
            message_text = ''
            status_order_text = ''
            if status_order == rq.OrderStatus.new:
                status_order_text = '🔔 Новый 🔔'
            elif status_order == rq.OrderStatus.cancel:
                status_order_text = '🚫 Отмененный 🚫'
            elif status_order == rq.OrderStatus.work:
                status_order_text = '🛠 В работе 🛠'
            elif status_order == rq.OrderStatus.complete:
                status_order_text = '✅ Выполненный ✅'
            elif status_order == rq.OrderStatus.unclaimed:
                status_order_text = '🔕 Невостребованный 🔕'
            message_text += f'<b>{status_order_text} заказ № {order.id_bitrix}</b>\n\n' \
                            f'<b>Клиент:</b>\n' \
                            f'<i>Имя:</i> {name}\n' \
                            f'<i>Телефон: {order.client_phone}</i>\n' \
                            f'<i>Адрес:</i> {address}\n\n' \
                            f'<b>Зaявка</b>\n' \
                            f'<i>Тип работы:</i> {order.task_type_work}\n' \
                            f'<i>Детали работы:</i> {order.task_detail}\n\n'
            if status_order in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
                message_text += f'<i>Мастер:</i> @{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                                f'tg_id{order.tg_executor}\n'
            if status_order == rq.OrderStatus.cancel:
                message_text += f'<i>Причина отказа:</i> {order.reason_of_refusal}\n'
            await callback.message.answer(text=message_text,
                                          reply_markup=keyboard,
                                          parse_mode='html')
    await callback.answer()


# <<
@router.callback_query(F.data.startswith('status_order_back_'))
async def process_back(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Пагинация назад
    :param callback: int(callback.data.split('_')[1]) номер блока для вывода
    :param state:
    :return:
    """
    logging.info(f'process_back: {callback.message.chat.id}')
    data = await state.get_data()
    status_order = data['status_order']
    models_orders = await rq.get_orders_status(status=status_order)
    list_orders = []
    for order in models_orders:
        list_orders.append(order)
    count_block = len(list_orders)
    num_block = int(callback.data.split('_')[3]) - 1
    if num_block < 0:
        num_block = count_block - 1
    keyboard = kb.keyboards_order_item(list_orders=list_orders, block=num_block, status_order=status_order)
    try:
        order = list_orders[num_block]
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
        if order.task_saratov_area != 'None':
            address += f'Саратовская область, {order.task_saratov_area}, {order.task_street}'
            # Формируем карточку заказа
            message_text = ''
            status_order_text = ''
            if status_order == rq.OrderStatus.new:
                status_order_text = '🔔 Новый 🔔'
            elif status_order == rq.OrderStatus.cancel:
                status_order_text = '🚫 Отмененный 🚫'
            elif status_order == rq.OrderStatus.work:
                status_order_text = '🛠 В работе 🛠'
            elif status_order == rq.OrderStatus.complete:
                status_order_text = '✅ Выполненный ✅'
            elif status_order == rq.OrderStatus.unclaimed:
                status_order_text = '🔕 Невостребованный 🔕'
            message_text += f'<b>{status_order_text} заказ № {order.id_bitrix}</b>\n\n' \
                            f'<b>Клиент:</b>\n' \
                            f'<i>Имя:</i> {name}\n' \
                            f'<i>Телефон: {order.client_phone}</i>\n' \
                            f'<i>Адрес:</i> {address}\n\n' \
                            f'<b>Заявка</b>\n' \
                            f'<i>Тип работы:</i> {order.task_type_work}\n' \
                            f'<i>Детали работы:</i> {order.task_detail}\n\n'
            if status_order in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
                message_text += f'<i>Мастер:</i> @{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                                f'tg_id{order.tg_executor}\n'
            if status_order == rq.OrderStatus.cancel:
                message_text += f'<i>Причина отказа:</i> {order.reason_of_refusal}\n'
            await callback.message.answer(text=message_text,
                                          reply_markup=keyboard,
                                          parse_mode='html')
    except TelegramBadRequest:
        order = list_orders[num_block]
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
        if order.task_saratov_area != 'None':
            address += f'Саратовская область, {order.task_saratov_area}, {order.task_street}'
            # Формируем карточку заказа
            message_text = ''
            status_order_text = ''
            if status_order == rq.OrderStatus.new:
                status_order_text = '🔔 Новый 🔔'
            elif status_order == rq.OrderStatus.cancel:
                status_order_text = '🚫 Отмененный 🚫'
            elif status_order == rq.OrderStatus.work:
                status_order_text = '🛠 В работе 🛠'
            elif status_order == rq.OrderStatus.complete:
                status_order_text = '✅ Выполненный ✅'
            elif status_order == rq.OrderStatus.unclaimed:
                status_order_text = '🔕 Невостребованный 🔕'
            message_text += f'<b>{status_order_text} заказ № {order.id_bitrix}</b>\n\n' \
                            f'<b>Клиент:</b>\n' \
                            f'<i>Имя:</i> {name}\n' \
                            f'<i>Телефон: {order.client_phone}</i>\n' \
                            f'<i>Адрес:</i> {address}\n\n' \
                            f'<b>Зaявка</b>\n' \
                            f'<i>Тип работы:</i> {order.task_type_work}\n' \
                            f'<i>Детали работы:</i> {order.task_detail}\n\n'
            if status_order in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
                message_text += f'<i>Мастер:</i> @{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                                f'tg_id{order.tg_executor}\n'
            if status_order == rq.OrderStatus.cancel:
                message_text += f'<i>Причина отказа:</i> {order.reason_of_refusal}\n'
            await callback.message.answer(text=message_text,
                                          reply_markup=keyboard,
                                          parse_mode='html')
    await callback.answer()


@router.callback_query(F.data.startswith('detail_order_'))
async def show_detail_info_order(callback: CallbackQuery) -> None:
    """
    Предоставление детальной информации о заказе
    :param callback:
    :return:
    """
    logging.info(f'show_detail_info_order')
    id_order = int(callback.data.split('_')[-1])
    order = await rq.get_order_id(id_order=id_order)
    detail_text = order.order_detail_text
    detail_photo = order.order_detail_photo
    # детальной информации нет
    if detail_photo == 'None' and detail_text == 'None':
        await callback.message.edit_text(text=f'<b>Заказ: {order.id_bitrix}</b>\n\n'
                                              f'Дополнительные материалы не добавлены в базу данных',
                                         reply_markup=kb.keyboard_back_item(),
                                         parse_mode='html')
    else:
        # есть и фотографии и текст
        if detail_photo != 'None' and detail_text != "None":
            caption = f'<b>Заказ: {order.id_bitrix}</b>\n\n' + detail_text
            list_photo = [item for item in detail_photo.split('///') if item]
            if len(list_photo) > 1:
                media = []
                for image in list_photo:
                    media.append(InputMediaPhoto(media=image))
                await callback.message.answer_media_group(media=media)
                await callback.message.answer(text=caption,
                                              reply_markup=kb.keyboard_back_item(),
                                              parse_mode='html')
            else:
                await callback.message.answer_photo(photo=list_photo[0], caption=caption,
                                                    reply_markup=kb.keyboard_back_item(),
                                                    parse_mode='html')
        # есть только фото
        elif detail_photo != 'None' and detail_text == "None":
            caption = f'<b>Заказ: {id_order}</b>\n\n'
            list_photo = [item for item in detail_photo.split('///') if item]
            if len(list_photo) > 1:
                media = []
                for image in list_photo:
                    media.append(InputMediaPhoto(media=image))
                await callback.message.answer_media_group(media=media)
                await callback.message.answer(text=caption,
                                              reply_markup=kb.keyboard_back_item(),
                                              parse_mode='html')
            else:
                await callback.message.answer_photo(photo=list_photo[0], caption=caption,
                                                    reply_markup=kb.keyboard_back_item(),
                                                    parse_mode='html')
        # есть только текст
        elif detail_photo == 'None' and detail_text != "None":
            caption = f'<b>Заказ: {id_order}</b>\n\n' + detail_text
            await callback.message.answer(text=caption,
                                          reply_markup=kb.keyboard_back_item(),
                                          parse_mode='html')
    await callback.answer()


@router.callback_query(F.data == 'back_order')
async def show_detail_info_order(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Возврат к списку заказов
    :param callback:
    :param state:
    :return:
    """
    data = await state.get_data()
    status_order = data['status_order']
    models_orders = await rq.get_orders_status(status=status_order)
    list_orders = []
    for order in models_orders:
        list_orders.append(order)
    count_block = len(list_orders)
    if count_block == 0:
        await callback.answer(text=f'В разделе нет заказов', show_alert=True)
        return
    # выводим карточки
    keyboard = kb.keyboards_order_item(list_orders=list_orders, block=0, status_order=status_order)
    order = list_orders[0]
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
    if order.task_saratov_area != 'None':
        address += f'Саратовская область, {order.task_saratov_area}, {order.task_street}'
        # Формируем карточку заказа
        message_text = ''
        status_order_text = ''
        if status_order == rq.OrderStatus.new:
            status_order_text = '🔔 Новый 🔔'
        elif status_order == rq.OrderStatus.cancel:
            status_order_text = '🚫 Отмененный 🚫'
        elif status_order == rq.OrderStatus.work:
            status_order_text = '🛠 В работе 🛠'
        elif status_order == rq.OrderStatus.complete:
            status_order_text = '✅ Выполненный ✅'
        elif status_order == rq.OrderStatus.unclaimed:
            status_order_text = '🔕 Невостребованный 🔕'
        message_text += f'<b>{status_order_text} заказ № {order.id_bitrix}</b>\n\n' \
                        f'<b>Клиент:</b>\n' \
                        f'<i>Имя:</i> {name}\n' \
                        f'<i>Телефон: {order.client_phone}</i>\n' \
                        f'<i>Адрес:</i> {address}\n\n' \
                        f'<b>Заявка</b>\n' \
                        f'<i>Тип работы:</i> {order.task_type_work}\n' \
                        f'<i>Детали работы:</i> {order.task_detail}\n\n'
        if status_order in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
            message_text += f'<i>Мастер:</i> @{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                            f'tg_id{order.tg_executor}\n'
        if status_order == rq.OrderStatus.cancel:
            message_text += f'<i>Причина отказа:</i> {order.reason_of_refusal}\n'
        await callback.message.answer(text=message_text,
                                      reply_markup=keyboard,
                                      parse_mode='html')


@router.callback_query(F.data.startswith('set_complete_'))
async def process_set_order_complete(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Устанавливаем заказ как завершенный
    :param callback:
    :param state:
    :return:
    """
    logging.info(f'process_set_order_complete')
    await callback.message.answer(text='Пришлите стоимость заказа')
    await state.update_data(id_order=callback.data.split('_')[-1])
    await callback.answer()
    await state.set_state(OrderPersonal.set_amount)


@router.message(StateFilter(OrderPersonal.set_amount), lambda message: message.text.isnumeric())
async def get_amount_order(message: Message, state: FSMContext):
    """
    Получение стоимости выполненного заказа
    :param message:
    :param state:
    :return:
    """
    logging.info(f'get_amount_order')
    amount = float(message.text)
    data = await state.get_data()
    id_order = data['id_order']
    await rq.set_order_amount(id_order=id_order, amount=amount)
    await rq.set_order_status(id_order=id_order, status=rq.OrderStatus.complete)
    await message.answer(text='Стоимость добавлена в заказ!\n'
                              'Заказ переведен в статус "Выполненные".')
    await state.set_state(default_state)


@router.message(StateFilter(OrderPersonal.set_amount))
async def get_amount_order_error(message: Message):
    """
    Ошибка при вводе стоимости заказа
    :param message:
    :return:
    """
    logging.info(f'get_amount_order_error')
    await message.answer(text='Введите целое число. Повторите ввод')


@router.callback_query(F.data.startswith('set_new_'))
async def process_set_order_new(callback: CallbackQuery) -> None:
    """
    Возвращение заказа из отмененного
    :param callback:
    :return:
    """
    logging.info(f'process_set_order_new')
    id_order = int(callback.data.split('_')[-1])
    await rq.set_order_status(id_order=id_order, status=rq.OrderStatus.new)
    await callback.answer(text=f'Заказ {id_order} переведен в раздел "Новый"', show_alert=True)


@router.callback_query(F.data.startswith('set_close_'))
async def process_set_order_close(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Закрытие заказа с указанием комментария
    :param callback:
    :param state:
    :return:
    """
    logging.info(f'process_set_order_close')
    id_order = int(callback.data.split('_')[-1])
    await state.update_data(id_order=id_order)
    await callback.message.answer(text='Пришлите причину закрытия заказа')
    await state.set_state(OrderPersonal.set_comment)


@router.message(F.text, StateFilter(OrderPersonal.set_comment))
async def get_comment_close_order(message: Message, state: FSMContext):
    """
    Закрытие заказа с указанием комментария
    :param message:
    :param state:
    :return:
    """
    data = await state.get_data()
    id_order = data['id_order']
    comment = message.text
    await rq.set_order_reason_of_refusal(id_order=id_order, refusal=comment)
    await message.answer(text=f'Заказ {id_order} закрыт')
    await state.set_state(default_state)


@router.callback_query(F.data == 'user_order_find')
async def process_set_order_close(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Запрос номер
    :param callback:
    :param state:
    :return:
    """
    await callback.message.answer(text=f'🔎 Пришлите ID заказа:')
    await state.set_state(OrderPersonal.search_id)
    await callback.answer()


@router.message(F.text, StateFilter(OrderPersonal.search_id))
async def search_order_id_bitrix(message: Message, state: FSMContext):
    """
    Поиск заказа по его ID в системе bitrix
    :param message:
    :param state:
    :return: 
    """
    try:
        bitrix_id = int(message.text)
    except ValueError:
        await message.answer(text='ID заказа должно быть целым числом!')
        await state.set_state(default_state)
        return
    order = await rq.get_order_bitrix_id(bitrix_id=bitrix_id)
    if order:

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
        if order.task_saratov_area != 'None':
            address += f'Саратовская область, {order.task_saratov_area}, {order.task_street}'
        # Формируем карточку заказа
        message_text = ''
        status_order_text = ''
        status_order = order.status
        if status_order == rq.OrderStatus.new:
            status_order_text = '🔔 Новый 🔔'
        elif status_order == rq.OrderStatus.cancel:
            status_order_text = '🚫 Отмененный 🚫'
        elif status_order == rq.OrderStatus.work:
            status_order_text = '🛠 В работе 🛠'
        elif status_order == rq.OrderStatus.complete:
            status_order_text = '✅ Выполненный ✅'
        elif status_order == rq.OrderStatus.unclaimed:
            status_order_text = '🔕 Невостребованный 🔕'
        message_text += f'<b>{status_order_text} заказ № {order.id_bitrix}</b>\n\n' \
                        f'<b>Клиент:</b>\n' \
                        f'<i>Имя:</i> {name}\n' \
                        f'<i>Телефон: {order.client_phone}</i>\n' \
                        f'<i>Адрес:</i> {address}\n\n' \
                        f'<b>Заявка</b>\n' \
                        f'<i>Тип работы:</i> {order.task_type_work}\n' \
                        f'<i>Детали работы:</i> {order.task_detail}\n\n'
        if status_order in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
            message_text += f'<i>Мастер:</i> @{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                            f'tg_id{order.tg_executor}\n'
        if status_order == rq.OrderStatus.cancel:
            message_text += f'<i>Причина отказа:</i> {order.reason_of_refusal}\n'
        await message.answer(text=message_text,
                             parse_mode='html')
    else:
        await message.answer(text=f'Заказ не найден!')
    await state.set_state(default_state)
