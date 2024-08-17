import pandas as pd
from database.requests import get_all_users
from database.models import Order
import database.requests as rq


async def list_users_to_exel():
    dict_stat = {"№ п/п": [], "ID_telegram": [], "username": []}
    i = 0
    list_user = await get_all_users()
    for user in list_user:
        i += 1
        dict_stat["№ п/п"].append(i)
        dict_stat["ID_telegram"].append(user.tg_id)
        dict_stat["username"].append(user.username)
    df_stat = pd.DataFrame(dict_stat)
    with pd.ExcelWriter(path='./list_user.xlsx', engine='xlsxwriter') as writer:
        df_stat.to_excel(writer, sheet_name=f'Список пользователей', index=False)


async def get_report():

    dict_report = {"№ п/п": [], "ID": [], "Дата создания": [], "Дата завершения": [], "ID исполнителя": [],
                   "username исполнителя": []}
    i = 0
    orders = await rq.get_orders_status(status=rq.OrderStatus.complete)
    for order in orders:
        i += 1
        dict_report["№ п/п"].append(i)
        dict_report["ID"].append(order.id)
        dict_report["Дата создания"].append(order.data_create)
        dict_report["Дата завершения"].append(order.data_complete)
        dict_report["ID исполнителя"].append(order.tg_executor)
        user = await rq.get_user_tg_id(tg_id=order.tg_executor)
        if user:
            dict_report["username исполнителя"].append(user.username)
        else:
            dict_report["username исполнителя"].append('None')
    df_stat = pd.DataFrame(dict_report)
    with pd.ExcelWriter(path='./list_report.xlsx', engine='xlsxwriter') as writer:
        df_stat.to_excel(writer, sheet_name=f'Отчет', index=False)
