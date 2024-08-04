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


@router.message(F.text == 'Баланс')
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


@router.message(F.text == 'Мои заказы')
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
    await callback.message.edit_text(text=f'<b>Клиент:</b>\n'
                                          f'{list_orders[0].client_info}\n'
                                          f'<b>Заказ:</b>\n'
                                          f'{list_orders[0].task_info}\n'
                                          f'<b>Стоимость:</b> {list_orders[0].amount}\n',
                                     reply_markup=keyboard,
                                     parse_mode='html')


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
        await callback.message.edit_text(text=f'<b>Клиент:</b>\n'
                                              f'{list_orders[num_block].client_info}\n'
                                              f'<b>Заказ:</b>\n'
                                              f'{list_orders[num_block].task_info}\n'
                                              f'<b>Стоимость:</b> {list_orders[num_block].amount}\n',
                                         reply_markup=keyboard,
                                         parse_mode='html')
    except TelegramBadRequest:
        await callback.message.edit_text(text=f'<b>Клиeнт:</b>\n'
                                              f'{list_orders[num_block].client_info}\n'
                                              f'<b>Заказ:</b>\n'
                                              f'{list_orders[num_block].task_info}\n'
                                              f'<b>Стоимость:</b> {list_orders[num_block].amount}\n',
                                         reply_markup=keyboard,
                                         parse_mode='html')


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
        await callback.message.edit_text(text=f'<b>Клиент:</b>\n'
                                              f'{list_orders[num_block].client_info}\n'
                                              f'<b>Заказ:</b>\n'
                                              f'{list_orders[num_block].task_info}\n'
                                              f'<b>Стоимость:</b> {list_orders[num_block].amount}\n',
                                         reply_markup=keyboard,
                                         parse_mode='html')
    except TelegramBadRequest:
        await callback.message.edit_text(text=f'<b>Клиeнт:</b>\n'
                                              f'{list_orders[num_block].client_info}\n'
                                              f'<b>Заказ:</b>\n'
                                              f'{list_orders[num_block].task_info}\n'
                                              f'<b>Стоимость:</b> {list_orders[0].amount}\n',
                                         reply_markup=keyboard,
                                         parse_mode='html')


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
        await callback.message.edit_text(text=f'<b>Заказ: {id_order}</b>\n\n'
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


@router.callback_query(F.data == 'back_order')
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
    await callback.message.edit_text(text=f'<b>Клиент:</b>\n'
                                          f'{list_orders[0].client_info}\n'
                                          f'<b>Заказ:</b>\n'
                                          f'{list_orders[0].task_info}\n'
                                          f'<b>Стоимость:</b> {list_orders[0].amount}\n',
                                     reply_markup=keyboard,
                                     parse_mode='html')


@router.callback_query(F.data.startswith('set_work_'))
async def process_set_order_work(callback: CallbackQuery) -> None:
    """
    Взять заказ
    :param callback:
    :return:
    """
    logging.info(f'process_set_order_work')
    models_orders = await rq.get_order_idtg_and_status(tg_id=callback.message.chat.id,
                                                       status=rq.OrderStatus.new)
    list_orders = []
    for order in models_orders:
        list_orders.append(order)
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
        await callback.message.answer(text=f'Вы взяли в работу заказ {callback.data.split("_")[-1]}: '
                                           f'Подробная информация о заказе.')
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
async def get_details_order(message: Message, state: FSMContext):
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
    elif message.photo:
        order = await rq.get_order_id(id_order=id_order)
        if order.order_detail_photo == "None":
            await rq.set_order_detail_photo(id_order=id_order,
                                            detail_photo=f'{message.photo[-1].file_id}///')
        elif "///" in order.order_detail_photo:
            detail_photo = order.order_detail_photo
            detail_photo += f'{message.photo[-1].file_id}///'
            await rq.set_order_detail_photo(id_order=id_order, detail_photo=detail_photo)
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
    await rq.set_order_reason_of_refusal(id_order=id_order, refusal=message.text)
    await rq.set_order_status(id_order=id_order, status=rq.OrderStatus.cancel)
    await message.answer(text=f'Заказ {id_order} помечен как "Отменен". Информация передана диспетчеру.')
    dispatchers = await rq.get_users_role(role=rq.UserRole.dispatcher)
    if dispatchers:
        for dispatcher in dispatchers:
            try:
                await bot.send_message(chat_id=dispatcher.tg_id,
                                       text=f'Пользователь @{message.from_user.username}'
                                            f' перевел заказ {id_order} в статус "Отменен".\n'
                                            f'Причина: {message.text}')
            except TelegramBadRequest:
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
    await callback.message.answer(text=f'Заказ {id_order} помечен как выполненный. Информация передана менеджеру')
    managers = await rq.get_users_role(role=rq.UserRole.manager)
    if managers:
        for manager in managers:
            try:
                await bot.send_message(chat_id=manager.tg_id,
                                       text=f'Пользователь @{callback.from_user.username}'
                                            f' завершил заказ {id_order}')
            except TelegramBadRequest:
                pass
