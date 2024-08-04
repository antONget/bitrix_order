import pandas as pd
from database.requests import get_all_users
from database.models import Order
import database.requests as rq


async def list_users_to_exel():
    dict_stat = {"№ п/п": [], "ID_telegram": [], "username": [], "role": []}
    i = 0
    list_user = await get_all_users()
    for user in list_user:
        i += 1
        dict_stat["№ п/п"].append(i)
        dict_stat["ID_telegram"].append(user.tg_id)
        dict_stat["username"].append(user.username)
        dict_stat["role"].append(user.role)
    df_stat = pd.DataFrame(dict_stat)
    with pd.ExcelWriter(path='./list_user.xlsx', engine='xlsxwriter') as writer:
        df_stat.to_excel(writer, sheet_name=f'Список пользователей', index=False)


async def get_report():

    dict_report = {"№ п/п": [], "ID": [], "Дата создания": []}
    i = 0
    orders = await rq.get_orders_all()
    for order in orders:
        i += 1
        dict_report["№ п/п"].append(i)
        dict_report["ID"].append(order.id)
        dict_report["Дата создания"].append(order.data_create)
    df_stat = pd.DataFrame(dict_report)
    with pd.ExcelWriter(path='./list_report.xlsx', engine='xlsxwriter') as writer:
        df_stat.to_excel(writer, sheet_name=f'Отчет', index=False)
