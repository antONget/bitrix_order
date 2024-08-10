from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.filters import StateFilter
import aiogram_calendar
from filter.admin_filter import check_super_admin
from datetime import datetime
import logging
from services.get_exel import get_report
router = Router()


class Report(StatesGroup):
    period_start = State()
    period_finish = State()


@router.message(F.text == '📄 Отчеты 📄')
async def add_task(message: Message, state: FSMContext) -> None:
    """
    Получение отчета за выбранный период
    :param message:
    :param state:
    :return:
    """
    logging.info(f'add_task {message.chat.id}')
    if check_super_admin(telegram_id=message.chat.id):
        calendar = aiogram_calendar.SimpleCalendar(show_alerts=True)
        calendar.set_dates_range(datetime(2024, 1, 1), datetime(2030, 12, 31))
        # получаем текущую дату
        current_date = datetime.now()
        # преобразуем ее в строку
        date1 = current_date.strftime('%m/%d/%y')
        # преобразуем дату в список
        list_date1 = date1.split('/')
        await message.answer(
            "Выберите начало периода, для получения отчета:",
            reply_markup=await calendar.start_calendar(year=int('20'+list_date1[2]), month=int(list_date1[0]))
        )
        await state.set_state(Report.period_start)
    else:
        await message.answer(text='У вас недостаточно прав для этого функционала')


async def process_buttons_press_finish(callback: CallbackQuery, state: FSMContext):
    calendar = aiogram_calendar.SimpleCalendar(show_alerts=True)
    calendar.set_dates_range(datetime(2024, 1, 1), datetime(2030, 12, 31))
    # получаем текущую дату
    current_date = datetime.now()
    # преобразуем ее в строку
    date1 = current_date.strftime('%m/%d/%y')
    # преобразуем дату в список
    list_date1 = date1.split('/')
    await callback.message.answer(
        "Выберите конец периода, для получения отчета:",
        reply_markup=await calendar.start_calendar(year=int('20'+list_date1[2]), month=int(list_date1[0]))
    )
    await state.set_state(Report.period_finish)


@router.callback_query(aiogram_calendar.SimpleCalendarCallback.filter(), StateFilter(Report.period_start))
async def process_simple_calendar_start(callback_query: CallbackQuery, callback_data: CallbackData, state: FSMContext):
    calendar = aiogram_calendar.SimpleCalendar(show_alerts=True)
    calendar.set_dates_range(datetime(2022, 1, 1), datetime(2025, 12, 31))
    selected, date = await calendar.process_selection(callback_query, callback_data)
    if selected:
        await callback_query.message.edit_text(
            f'Начало периода {date.strftime("%d/%m/%y")}')
        await state.update_data(period_start=date.strftime("%m/%d/%y"))
        await process_buttons_press_finish(callback_query, state=state)


@router.callback_query(aiogram_calendar.SimpleCalendarCallback.filter(), StateFilter(Report.period_finish))
async def process_simple_calendar_finish(callback: CallbackQuery, callback_data: CallbackData, state: FSMContext):
    calendar = aiogram_calendar.SimpleCalendar(show_alerts=True)
    calendar.set_dates_range(datetime(2022, 1, 1), datetime(2025, 12, 31))
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        await callback.message.edit_text(
            f'Конец периода {date.strftime("%d/%m/%y")}')
        await state.update_data(period_finish=date.strftime("%m/%d/%y"))
        await state.update_data(salesperiod=0)
        await state.set_state(default_state)
        # await callback.message.answer(text='Раздел в разработке. Здесь будет формироваться отчет по всем заказам')
        await get_report()
        file_path = "list_report.xlsx"
        await callback.message.answer_document(FSInputFile(file_path))
    await state.set_state(default_state)