from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from aiogram.filters import StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state

from config_data.config import Config, load_config
import database.requests as rq
import keyboards.keyboard_user as kb

from aiogram.exceptions import TelegramBadRequest
from datetime import datetime
import logging


router = Router()
config: Config = load_config()


class UserOrder(StatesGroup):
    reason_of_refusal = State()
    add_detail = State()
    search_id = State()


@router.message(F.text == '💰 Баланс 💰')
async def get_balance_user(message: Message) -> None:
    """
    Получаем стоимость завершенных пользователем заказов
    :param message:
    :return:
    """
    logging.info(f'get_balance_user {message.chat.id}')
    orders = await rq.get_order_idtg_and_status(tg_id=message.chat.id, status=rq.OrderStatus.complete)
    if orders:
        balance = 0
        count_complete_user = 0
        for order in orders:
            count_complete_user += 1
            balance += order.amount
        await message.answer(text=f'Вы выполнили {count_complete_user} заказ(а) на сумму {balance} руб.')
    else:
        await message.answer(text=f'Вы не завершили еще ни одного заказа')


@router.message(F.text == '💼 Меню заказов 💼')
async def get_balance_user(message: Message) -> None:
    """
    Получаем заказы для исполнителя
    :param message:
    :return:
    """
    logging.info(f'get_balance_user {message.chat.id}')
    await message.answer(text='Выберите раздел',
                         reply_markup=await kb.keyboard_select_status_order(tg_id=message.chat.id))


@router.callback_query(F.data.startswith('user_order_status_'))
async def show_merch_slider(callback: CallbackQuery, state: FSMContext):
    """
    Выводим карточки выбранного статуса в блоках
    :param callback:
    :param state:
    :return:
    """
    logging.info(f'show_merch_slider: {callback.message.chat.id}')
    status_order = callback.data.split('_')[3]
    await state.update_data(status_order=status_order)
    if status_order == rq.OrderStatus.new:
        models_orders = await rq.get_orders_status(status=rq.OrderStatus.new)
    else:
        models_orders = await rq.get_order_idtg_and_status(tg_id=callback.message.chat.id, status=status_order)
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
    status_order_text = ''
    message_text = ''
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
    # 1. Формируем общую часть заказа для всех статусов
    message_text += f'{status_order_text} заказ № <b>{order.id_bitrix}</b>\n' \
                    f'Дата создания заказа: <b>{order.data_create}</b>\n\n' \

    # 2. Формируем контактные данные клиента для завершенных заказов
    if order.status != rq.OrderStatus.new:
        message_text += f'<b>Клиент:</b>\n' \
                        f'Имя: <b>{name}</b>\n' \
                        f'Телефон: <code>{order.client_phone}<code>\n\n'

    message_text += f'<b>Адрес:</b>'
    if order.task_saratov != 'None':
        if 'город' not in order.task_saratov:
            message_text += f'Город: <b>{"Саратов"}</b>\n'
            if order.task_saratov:
                message_text += f'Район: <b>{order.task_saratov}</b>\n'
        else:
            message_text += f'Город: <b>{"Саратов"}</b>\n'
    elif order.task_engels != 'None':
        if 'город' not in order.task_engels:
            message_text += f'Город: <b>{"Энгельс"}</b>\n'
            if order.task_engels:
                message_text += f'Район: <b>{order.task_engels}</b>\n'
        else:
            message_text += f'Город: <b>{"Энгельс"}</b>\n'
    elif order.task_saratov_area != 'None':
        message_text += f'Саратовская область:\n' \
                        f'Район: <b>{order.task_saratov_area}</b>\n'
    if order.task_street:
        message_text += f'Улица: <b>{order.task_street.split("|")[0]}</b>\n\n'
    # 3. Формируем информацию о задаче
    message_text += f'<b>Заявка</b>\n' \
                    f'Тип работы: <b>{order.task_type_work}</b>\n' \
                    f'Детали работы: <b>{order.task_detail}</b>\n\n'

    # 4. Формируем информацию о заявках в работе выполненных и отменных
    if order.status in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
        message_text += f'Мастер: <b>@{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                        f'tg_id{order.tg_executor}</b>\n'

    # 5. Формируем причину отказа
    if order.status == rq.OrderStatus.cancel:
        message_text += f'Причина отказа: <b>{order.reason_of_refusal}</b>\n'
    # 5. Формируем стоимость заказа
    elif order.status == rq.OrderStatus.complete:
        message_text += f'Стоимость заказа: <b>{order.amount}</b>'
    await callback.message.answer(text=message_text,
                                  reply_markup=keyboard,
                                  parse_mode='html')
    await callback.answer()


# >>
@router.callback_query(F.data.startswith('user_order_forward_'))
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
    if status_order == rq.OrderStatus.new:
        models_orders = await rq.get_orders_status(status=rq.OrderStatus.new)
    else:
        models_orders = await rq.get_order_idtg_and_status(tg_id=callback.message.chat.id, status=status_order)
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

        status_order_text = ''
        message_text = ''
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
        # 1. Формируем общую часть заказа для всех статусов
        message_text += f'{status_order_text} заказ № <b>{order.id_bitrix}</b>\n' \
                        f'Дата создания заказа: <b>{order.data_create}</b>\n\n' \

        # 2. Формируем контактные данные клиента для завершенных заказов
        if order.status != rq.OrderStatus.new:
            message_text += f'<b>Клиент:</b>\n' \
                            f'Имя: <b>{name}</b>\n' \
                            f'Телефон: <code>{order.client_phone}<code>\n\n'

        message_text += f'<b>Адрес:</b>'
        if order.task_saratov != 'None':
            if 'город' not in order.task_saratov:
                message_text += f'Город: <b>{"Саратов"}</b>\n'
                if order.task_saratov:
                    message_text += f'Район: <b>{order.task_saratov}</b>\n'
            else:
                message_text += f'Город: <b>{"Саратов"}</b>\n'
        elif order.task_engels != 'None':
            if 'город' not in order.task_engels:
                message_text += f'Город: <b>{"Энгельс"}</b>\n'
                if order.task_engels:
                    message_text += f'Район: <b>{order.task_engels}</b>\n'
            else:
                message_text += f'Город: <b>{"Энгельс"}</b>\n'
        elif order.task_saratov_area != 'None':
            message_text += f'Саратовская область:\n' \
                            f'Район: <b>{order.task_saratov_area}</b>\n'
        if order.task_street:
            message_text += f'Улица: <b>{order.task_street.split("|")[0]}</b>\n\n'
        # 3. Формируем информацию о задаче
        message_text += f'<b>Заявка</b>\n' \
                        f'Тип работы: <b>{order.task_type_work}</b>\n' \
                        f'Детали работы: <b>{order.task_detail}</b>\n\n'

        # 4. Формируем информацию о заявках в работе выполненных и отменных
        if order.status in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
            message_text += f'Мастер: <b>@{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                            f'tg_id{order.tg_executor}</b>\n'

        # 5. Формируем причину отказа
        if order.status == rq.OrderStatus.cancel:
            message_text += f'Причина отказа: <b>{order.reason_of_refusal}</b>\n'
        # 5. Формируем стоимость заказа
        elif order.status == rq.OrderStatus.complete:
            message_text += f'Стоимость заказа: <b>{order.amount}</b>'
        await callback.message.answer(text=message_text,
                                      reply_markup=keyboard,
                                      parse_mode='html')
    except TelegramBadRequest:
        order = list_orders[num_block]
        name = ''
        for n in [order.client_second_name, order.client_name, order.client_last_name]:
            if n != 'None':
                name += f'{n} '

        status_order_text = ''
        message_text = ''
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
        # 1. Формируем общую часть заказа для всех статусов
        message_text += f'{status_order_text} зaказ № <b>{order.id_bitrix}</b>\n' \
                        f'Дата создания заказа: <b>{order.data_create}</b>\n\n' \

        # 2. Формируем контактные данные клиента для завершенных заказов
        if order.status != rq.OrderStatus.new:
            message_text += f'<b>Клиент:</b>\n' \
                            f'Имя: <b>{name}</b>\n' \
                            f'Телефон: <code>{order.client_phone}<code>\n\n'

        message_text += f'<b>Адрес:</b>'
        if order.task_saratov != 'None':
            if 'город' not in order.task_saratov:
                message_text += f'Город: <b>{"Саратов"}</b>\n'
                if order.task_saratov:
                    message_text += f'Район: <b>{order.task_saratov}</b>\n'
            else:
                message_text += f'Город: <b>{"Саратов"}</b>\n'
        elif order.task_engels != 'None':
            if 'город' not in order.task_engels:
                message_text += f'Город: <b>{"Энгельс"}</b>\n'
                if order.task_engels:
                    message_text += f'Район: <b>{order.task_engels}</b>\n'
            else:
                message_text += f'Город: <b>{"Энгельс"}</b>\n'
        elif order.task_saratov_area != 'None':
            message_text += f'Саратовская область:\n' \
                            f'Район: <b>{order.task_saratov_area}</b>\n'
        if order.task_street:
            message_text += f'Улица: <b>{order.task_street.split("|")[0]}</b>\n\n'
        # 3. Формируем информацию о задаче
        message_text += f'<b>Заявка</b>\n' \
                        f'Тип работы: <b>{order.task_type_work}</b>\n' \
                        f'Детали работы: <b>{order.task_detail}</b>\n\n'

        # 4. Формируем информацию о заявках в работе выполненных и отменных
        if order.status in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
            message_text += f'Мастер: <b>@{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                            f'tg_id{order.tg_executor}</b>\n'

        # 5. Формируем причину отказа
        if order.status == rq.OrderStatus.cancel:
            message_text += f'Причина отказа: <b>{order.reason_of_refusal}</b>\n'
        # 5. Формируем стоимость заказа
        elif order.status == rq.OrderStatus.complete:
            message_text += f'Стоимость заказа: <b>{order.amount}</b>'
        await callback.message.answer(text=message_text,
                                      reply_markup=keyboard,
                                      parse_mode='html')
    await callback.answer()


# <<
@router.callback_query(F.data.startswith('user_order_back_'))
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
    if status_order == rq.OrderStatus.new:
        models_orders = await rq.get_orders_status(status=rq.OrderStatus.new)
    else:
        models_orders = await rq.get_order_idtg_and_status(tg_id=callback.message.chat.id, status=status_order)
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

        status_order_text = ''
        message_text = ''
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
        # 1. Формируем общую часть заказа для всех статусов
        message_text += f'{status_order_text} заказ № <b>{order.id_bitrix}</b>\n' \
                        f'Дата создания заказа: <b>{order.data_create}</b>\n\n' \

        # 2. Формируем контактные данные клиента для завершенных заказов
        if order.status != rq.OrderStatus.new:
            message_text += f'<b>Клиент:</b>\n' \
                            f'Имя: <b>{name}</b>\n' \
                            f'Телефон: <code>{order.client_phone}<code>\n\n'

        message_text += f'<b>Адрес:</b>'
        if order.task_saratov != 'None':
            if 'город' not in order.task_saratov:
                message_text += f'Город: <b>{"Саратов"}</b>\n'
                if order.task_saratov:
                    message_text += f'Район: <b>{order.task_saratov}</b>\n'
            else:
                message_text += f'Город: <b>{"Саратов"}</b>\n'
        elif order.task_engels != 'None':
            if 'город' not in order.task_engels:
                message_text += f'Город: <b>{"Энгельс"}</b>\n'
                if order.task_engels:
                    message_text += f'Район: <b>{order.task_engels}</b>\n'
            else:
                message_text += f'Город: <b>{"Энгельс"}</b>\n'
        elif order.task_saratov_area != 'None':
            message_text += f'Саратовская область:\n' \
                            f'Район: <b>{order.task_saratov_area}</b>\n'
        if order.task_street:
            message_text += f'Улица: <b>{order.task_street.split("|")[0]}</b>\n\n'
        # 3. Формируем информацию о задаче
        message_text += f'<b>Заявка</b>\n' \
                        f'Тип работы: <b>{order.task_type_work}</b>\n' \
                        f'Детали работы: <b>{order.task_detail}</b>\n\n'

        # 4. Формируем информацию о заявках в работе выполненных и отменных
        if order.status in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
            message_text += f'Мастер: <b>@{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                            f'tg_id{order.tg_executor}</b>\n'

        # 5. Формируем причину отказа
        if order.status == rq.OrderStatus.cancel:
            message_text += f'Причина отказа: <b>{order.reason_of_refusal}</b>\n'
        # 5. Формируем стоимость заказа
        elif order.status == rq.OrderStatus.complete:
            message_text += f'Стоимость заказа: <b>{order.amount}</b>'
        await callback.message.answer(text=message_text,
                                      reply_markup=keyboard,
                                      parse_mode='html')
    except TelegramBadRequest:
        order = list_orders[num_block]
        name = ''
        for n in [order.client_second_name, order.client_name, order.client_last_name]:
            if n != 'None':
                name += f'{n} '

        status_order_text = ''
        message_text = ''
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
        # 1. Формируем общую часть заказа для всех статусов
        message_text += f'{status_order_text} зaказ № <b>{order.id_bitrix}</b>\n' \
                        f'Дата создания заказа: <b>{order.data_create}</b>\n\n' \

        # 2. Формируем контактные данные клиента для завершенных заказов
        if order.status != rq.OrderStatus.new:
            message_text += f'<b>Клиент:</b>\n' \
                            f'Имя: <b>{name}</b>\n' \
                            f'Телефон: <code>{order.client_phone}<code>\n\n'

        message_text += f'<b>Адрес:</b>'
        if order.task_saratov != 'None':
            if 'город' not in order.task_saratov:
                message_text += f'Город: <b>{"Саратов"}</b>\n'
                if order.task_saratov:
                    message_text += f'Район: <b>{order.task_saratov}</b>\n'
            else:
                message_text += f'Город: <b>{"Саратов"}</b>\n'
        elif order.task_engels != 'None':
            if 'город' not in order.task_engels:
                message_text += f'Город: <b>{"Энгельс"}</b>\n'
                if order.task_engels:
                    message_text += f'Район: <b>{order.task_engels}</b>\n'
            else:
                message_text += f'Город: <b>{"Энгельс"}</b>\n'
        elif order.task_saratov_area != 'None':
            message_text += f'Саратовская область:\n' \
                            f'Район: <b>{order.task_saratov_area}</b>\n'
        if order.task_street:
            message_text += f'Улица: <b>{order.task_street.split("|")[0]}</b>\n\n'
        # 3. Формируем информацию о задаче
        message_text += f'<b>Заявка</b>\n' \
                        f'Тип работы: <b>{order.task_type_work}</b>\n' \
                        f'Детали работы: <b>{order.task_detail}</b>\n\n'

        # 4. Формируем информацию о заявках в работе выполненных и отменных
        if order.status in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
            message_text += f'Мастер: <b>@{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                            f'tg_id{order.tg_executor}</b>\n'

        # 5. Формируем причину отказа
        if order.status == rq.OrderStatus.cancel:
            message_text += f'Причина отказа: <b>{order.reason_of_refusal}</b>\n'
        # 5. Формируем стоимость заказа
        elif order.status == rq.OrderStatus.complete:
            message_text += f'Стоимость заказа: <b>{order.amount}</b>'
        await callback.message.answer(text=message_text,
                                      reply_markup=keyboard,
                                      parse_mode='html')
    await callback.answer()


@router.callback_query(F.data.startswith('user_detail_order_'))
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
    if detail_photo == 'None' and detail_text == 'None':
        await callback.message.edit_text(text=f'<b>Заказ № {id_order}</b>\n\n'
                                              f'Дополнительные материалы не добавлены в базу данных',
                                         reply_markup=kb.keyboard_back_item(),
                                         parse_mode='html')
    else:
        if detail_photo != 'None' and detail_text != "None":
            caption = f'<b>Заказ: {id_order}</b>\n\n' + detail_text
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
        elif detail_photo == 'None' and detail_text != "None":
            caption = f'<b>Заказ: {id_order}</b>\n\n' + detail_text
            await callback.message.answer(text=caption,
                                          reply_markup=kb.keyboard_back_item(),
                                          parse_mode='html')
    await callback.answer()


@router.callback_query(F.data == 'back_order_user')
async def show_detail_info_order(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Возврат к списку заказов из раздела ПОДРОБНЕЕ
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

    status_order_text = ''
    message_text = ''
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

    # 1. Формируем общую часть заказа для всех статусов
    message_text += f'{status_order_text} заказ № <b>{order.id_bitrix}</b>\n' \
                    f'Дата создания заказа: <b>{order.data_create}</b>\n\n' \

    # 2. Формируем контактные данные клиента для завершенных заказов
    if order.status != rq.OrderStatus.new:
        message_text += f'<b>Клиент:</b>\n' \
                        f'Имя: <b>{name}</b>\n' \
                        f'Телефон: <code>{order.client_phone}<code>\n\n'

    message_text += f'<b>Адрес:</b>'
    if order.task_saratov != 'None':
        if 'город' not in order.task_saratov:
            message_text += f'Город: <b>{"Саратов"}</b>\n'
            if order.task_saratov:
                message_text += f'Район: <b>{order.task_saratov}</b>\n'
        else:
            message_text += f'Город: <b>{"Саратов"}</b>\n'
    elif order.task_engels != 'None':
        if 'город' not in order.task_engels:
            message_text += f'Город: <b>{"Энгельс"}</b>\n'
            if order.task_engels:
                message_text += f'Район: <b>{order.task_engels}</b>\n'
        else:
            message_text += f'Город: <b>{"Энгельс"}</b>\n'
    elif order.task_saratov_area != 'None':
        message_text += f'Саратовская область:\n' \
                        f'Район: <b>{order.task_saratov_area}</b>\n'
    if order.task_street:
        message_text += f'Улица: <b>{order.task_street.split("|")[0]}</b>\n\n'
    # 3. Формируем информацию о задаче
    message_text += f'<b>Заявка</b>\n' \
                    f'Тип работы: <b>{order.task_type_work}</b>\n' \
                    f'Детали работы: <b>{order.task_detail}</b>\n\n'

    # 4. Формируем информацию о заявках в работе выполненных и отменных
    if order.status in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
        message_text += f'Мастер: <b>@{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                        f'tg_id{order.tg_executor}</b>\n'

    # 5. Формируем причину отказа
    if order.status == rq.OrderStatus.cancel:
        message_text += f'Причина отказа: <b>{order.reason_of_refusal}</b>\n'
    # 5. Формируем стоимость заказа
    elif order.status == rq.OrderStatus.complete:
        message_text += f'Стоимость заказа: <b>{order.amount}</b>'
    await callback.message.answer(text=message_text,
                                  reply_markup=keyboard,
                                  parse_mode='html')
    await callback.answer()


@router.callback_query(F.data.startswith('set_work_'))
async def process_set_order_work(callback: CallbackQuery) -> None:
    """
    Взять заказ
    :param callback:
    :return:
    """
    logging.info(f'process_set_order_work')
    list_orders = [order for order in await rq.get_order_idtg_and_status(tg_id=callback.message.chat.id,
                                                                         status=rq.OrderStatus.work)]

    count_block = len(list_orders)
    if count_block >= 3:
        await callback.answer(text=f'У вас в работе находится 3 заказа, вы не можете брать более 3х заказов'
                                   f' одновременно. Если вы завершили заказ то измените ее статус в раздели "Заказы"',
                              show_alert=True)
        return
    else:
        date_work = datetime.today().strftime('%H/%M/%S/%d/%m/%Y')
        await rq.set_order_work(id_order=int(callback.data.split('_')[-1]),
                                tg_executor=callback.message.chat.id,
                                data_work=date_work)
        order_id = int(callback.data.split("_")[-1])
        order = await rq.get_order_id(id_order=order_id)
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
        await callback.message.answer(text=f'<b>Вы взяли в работу заказ № {order.id_bitrix}</b>\n\n'
                                           f'<b>Клиент:</b>\n'
                                           f'<i>Имя:</i> {name}\n'
                                           f'<i>Телефон: {order.client_phone}</i>\n'
                                           f'<i>Адрес:</i> {address}\n\n'
                                           f'<b>Заявка</b>\n'
                                           f'<i>Тип работы:</i> {order.task_type_work}\n'
                                           f'<i>Детали работы:</i> {order.task_detail}\n'
                                           f'<i>Оплата:</i> {order.task_pay}\n'
                                           f'<i>Начало работ:</i> {order.task_begin}\n\n'
                                           f'Заказов в работе {count_block + 1}/3',
                                      parse_mode='html')
    await callback.answer()


@router.callback_query(F.data.startswith('change_status_'))
async def process_set_order_work(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Взять заказ
    :param callback:
    :param state:
    :return:
    """
    logging.info(f'process_set_order_work')
    await state.update_data(id_order=int(callback.data.split('_')[-1]))
    await callback.message.edit_text(text='Выберите раздел',
                                     reply_markup=kb.keyboard_change_status())
    await callback.answer()


@router.callback_query(F.data.startswith('add_detail_'))
async def process_add_detail_order(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Взять заказ
    :param callback:
    :param state:
    :return:
    """
    logging.info(f'process_set_order_work')
    id_order = int(callback.data.split('_')[-1])
    await state.update_data(id_order=id_order)
    await callback.message.answer(text=f'Пришлите фотографию или текст для добавления в заказ')
    await state.set_state(UserOrder.add_detail)
    await callback.answer()


@router.message(or_f(F.text, F.photo), StateFilter(UserOrder.add_detail))
async def get_details_order(message: Message, state: FSMContext, bot: Bot):
    """
    Получаем детали к заказу
    :param message:
    :param state:
    :return:
    """
    data = await state.get_data()
    id_order = data['id_order']
    if message.text:
        order = await rq.get_order_id(id_order=id_order)
        if order.order_detail_text == "None":
            await rq.set_order_detail_text(id_order=id_order, detail_text=f'{message.text}\n')
        else:
            detail_text = order.order_detail_text
            detail_text += f'{message.text}\n'
            await rq.set_order_detail_text(id_order=id_order, detail_text=detail_text)
        list_manager = await rq.get_users_role(role=rq.UserRole.manager)
        for manager in list_manager:
            try:
                await bot.send_message(chat_id=manager.tg_id,
                                       text=f'Мастер @{message.from_user.username} оставил текстовый комментарий'
                                            f' к заказу № {order.id_bitrix}')
            except:
                pass
        for admin in config.tg_bot.admin_ids.split(','):
            try:
                await bot.send_message(chat_id=int(admin),
                                       text=f'Мастер @{message.from_user.username} оставил текстовый комментарий'
                                            f' к заказу № {order.id_bitrix}')
            except:
                pass

    elif message.photo:
        order = await rq.get_order_id(id_order=id_order)
        if order.order_detail_photo == "None":
            await rq.set_order_detail_photo(id_order=id_order,
                                            detail_photo=f'{message.photo[-1].file_id}///')
        elif "///" in order.order_detail_photo:
            detail_photo = order.order_detail_photo
            detail_photo += f'{message.photo[-1].file_id}///'
            await rq.set_order_detail_photo(id_order=id_order, detail_photo=detail_photo)
        list_manager = await rq.get_users_role(role=rq.UserRole.manager)
        for manager in list_manager:
            try:
                await bot.send_message(chat_id=manager.tg_id,
                                       text=f'Мастер @{message.from_user.username} оставил фотоматериал'
                                            f' к заказу № {order.id_bitrix}')
            except:
                pass
        for admin in config.tg_bot.admin_ids.split(','):
            try:
                await bot.send_message(chat_id=int(admin),
                                       text=f'Мастер @{message.from_user.username} оставил фотоматериал'
                                            f' к заказу № {order.id_bitrix}')
            except:
                pass
    else:
        await message.answer(text='Можно добавлять только фото и текст')
    await message.answer(text='Добавить еще?',
                         reply_markup=kb.keyboard_continue_detail())


@router.callback_query(F.data == 'add_more')
async def process_add_more_detail(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Добавление еще материалов в заказ
    :param callback:
    :param state:
    :return:
    """
    logging.info('process_add_more_detail')
    await callback.message.answer(text=f'Пришлите фотографию или текст для добавления в заказ')
    await state.set_state(UserOrder.add_detail)
    await callback.answer()


@router.callback_query(F.data == 'add_not_more')
async def process_add_not_more_detail(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Добавление еще материалов в заказ
    :param callback:
    :param state:
    :return:
    """
    logging.info('process_add_more_detail')
    await callback.answer(text=f'Все материалы успешно добавлены', show_alert=True)
    await state.set_state(default_state)
    await callback.answer()


@router.callback_query(F.data == 'set_status_cancel')
async def process_set_order_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Отказаться от заказа. Отправляем информацию диспетчеру
    :param callback:
    :param state:
    :return:
    """
    logging.info(f'process_set_order_work')
    await callback.message.answer(text=f'Напишите причину отказа.')
    await state.set_state(UserOrder.reason_of_refusal)
    await callback.answer()


@router.message(F.text, StateFilter(UserOrder.reason_of_refusal))
async def get_reason_of_refusal(message: Message, state: FSMContext, bot: Bot):
    """
    Получаем причину отказа от заказа
    :param message:
    :param state:
    :param bot:
    :return:
    """
    logging.info(f'get_reason_of_refusal')
    data = await state.get_data()
    id_order = data['id_order']
    info_order = await rq.get_order_id(id_order=id_order)
    await rq.set_order_reason_of_refusal(id_order=id_order, refusal=message.text)
    await rq.set_order_status(id_order=id_order, status=rq.OrderStatus.cancel)
    await message.answer(text=f'Заказ № {info_order.id_bitrix} помечен как "Отменен". Информация передана диспетчеру.')
    dispatchers = await rq.get_users_role(role=rq.UserRole.dispatcher)
    if dispatchers:
        for dispatcher in dispatchers:
            try:
                await bot.send_message(chat_id=dispatcher.tg_id,
                                       text=f'Пользователь @{message.from_user.username}'
                                            f' перевел заказ № {info_order.id_bitrix} в статус "Отменен".\n'
                                            f'Причина: {message.text}')
            except TelegramBadRequest:
                pass
    for admin in config.tg_bot.admin_ids.split(','):
        try:
            await bot.send_message(chat_id=int(admin),
                                   text=f'Пользователь @{message.from_user.username}'
                                        f' перевел заказ № {info_order.id_bitrix} в статус "Отменен".\n'
                                        f'Причина: {message.text}')
        except:
            pass
    await state.set_state(default_state)


@router.callback_query(F.data == 'set_status_complete')
async def process_set_order_complete(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Завершить заказ и уведомление менеджера
    :param callback:
    :param state:
    :param bot:
    :return:
    """
    logging.info(f'process_set_order_complete')
    data = await state.get_data()
    id_order = data['id_order']
    info_order = await rq.get_order_id(id_order=id_order)
    await callback.message.answer(text=f'Заказ № {info_order.id_bitrix} помечен как выполненный. Информация передана менеджеру')
    managers = await rq.get_users_role(role=rq.UserRole.manager)
    if managers:
        for manager in managers:
            try:
                await bot.send_message(chat_id=manager.tg_id,
                                       text=f'Пользователь @{callback.from_user.username}'
                                            f' завершил заказ № {info_order.id_bitrix}')
            except TelegramBadRequest:
                pass
    for admin in config.tg_bot.admin_ids.split(','):
        try:
            await bot.send_message(chat_id=int(admin),
                                   text=f'Пользователь @{callback.from_user.username}'
                                        f' завершил заказ № {info_order.id_bitrix}')
        except:
            pass
    await callback.answer()


@router.callback_query(F.data == 'user_order_find')
async def process_set_order_close(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Запрос номер
    :param callback:
    :param state:
    :return:
    """
    await callback.message.answer(text=f'🔎 Пришлите ID заказа:')
    await state.set_state(UserOrder.search_id)
    await callback.answer()


@router.message(F.text, StateFilter(UserOrder.search_id))
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
        # Формируем карточку заказа
        message_text = ''
        status_order_text = ''
        if order.status == rq.OrderStatus.new:
            status_order_text = '🔔 Новый 🔔'
        elif order.status == rq.OrderStatus.cancel:
            status_order_text = '🚫 Отмененный 🚫'
        elif order.status == rq.OrderStatus.work:
            status_order_text = '🛠 В работе 🛠'
        elif order.status == rq.OrderStatus.complete:
            status_order_text = '✅ Выполненный ✅'
        elif order.status == rq.OrderStatus.unclaimed:
            status_order_text = '🔕 Невостребованный 🔕'

        # 1. Формируем общую часть заказа для всех статусов
        message_text += f'{status_order_text} заказ № <b>{order.id_bitrix}</b>\n' \
                        f'Дата создания заказа: <b>{order.data_create}</b>\n\n' \

        # 2. Формируем контактные данные клиента для завершенных заказов
        if order.status != rq.OrderStatus.new:
            message_text += f'<b>Клиент:</b>\n' \
                            f'Имя: <b>{name}</b>\n' \
                            f'Телефон: <code>{order.client_phone}<code>\n\n'

        message_text += f'<b>Адрес:</b>'
        if order.task_saratov != 'None':
            if 'город' not in order.task_saratov:
                message_text += f'Город: <b>{"Саратов"}</b>\n'
                if order.task_saratov:
                    message_text += f'Район: <b>{order.task_saratov}</b>\n'
            else:
                message_text += f'Город: <b>{"Саратов"}</b>\n'
        elif order.task_engels != 'None':
            if 'город' not in order.task_engels:
                message_text += f'Город: <b>{"Энгельс"}</b>\n'
                if order.task_engels:
                    message_text += f'Район: <b>{order.task_engels}</b>\n'
            else:
                message_text += f'Город: <b>{"Энгельс"}</b>\n'
        elif order.task_saratov_area != 'None':
            message_text += f'Саратовская область:\n' \
                            f'Район: <b>{order.task_saratov_area}</b>\n'
        if order.task_street:
            message_text += f'Улица: <b>{order.task_street.split("|")[0]}</b>\n\n'
        # 3. Формируем информацию о задаче
        message_text += f'<b>Заявка</b>\n' \
                        f'Тип работы: <b>{order.task_type_work}</b>\n' \
                        f'Детали работы: <b>{order.task_detail}</b>\n\n'

        # 4. Формируем информацию о заявках в работе выполненных и отменных
        if order.status in [rq.OrderStatus.work, rq.OrderStatus.complete, rq.OrderStatus.cancel]:
            message_text += f'Мастер: <b>@{(await rq.get_user_tg_id(order.tg_executor)).username}/' \
                            f'tg_id{order.tg_executor}</b>\n'

        # 5. Формируем причину отказа
        if order.status == rq.OrderStatus.cancel:
            message_text += f'Причина отказа: <b>{order.reason_of_refusal}</b>\n'
        # 5. Формируем стоимость заказа
        elif order.status == rq.OrderStatus.complete:
            message_text += f'Стоимость заказа: <b>{order.amount}</b>'

        models_orders = await rq.get_orders_status(status=order.status)
        list_orders = []
        i = -1
        for order in models_orders:
            i += 1
            list_orders.append(order)
            if bitrix_id == order.id_bitrix:
                block = i
        await state.update_data(status_order=order.status)
        keyboard = kb.keyboards_order_item(list_orders=list_orders, block=block, status_order=order.status)
        await message.answer(text=message_text,
                             reply_markup=keyboard,
                             parse_mode='html')
    else:
        await message.answer(text=f'Заказ не найден!')
    await state.set_state(default_state)