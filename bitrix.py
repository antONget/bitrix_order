# from fast_bitrix24 import Bitrix
from config_data.config import load_config, Config
import requests
import json
config: Config = load_config()
import asyncio


async def get_data_deal(id_deal: int) -> dict | bool | str:
    """
    Функция для получения полей заявки:
    Клиент: Имя, Телефон
    Заявка: Тип работы, Детали работы, Саратов, Начало работы, Оплата работы
    :param id_deal:
    :return:
    """
    contact_dict = {"Имя": {'NAME': 'None'},
                    "Фамилия": {"SECOND_NAME": 'None'},
                    "Отчество": {"LAST_NAME": 'None'},
                    "Телефон": {"PHONE": 'None'}}

    deal_dict = {"Тип работы": {"UF_CRM_1722889585844": 'None'},
                 "Детали работы:": {"UF_CRM_1723401519885": 'None'},
                 "Саратовская область ": {"UF_CRM_1723096401639": "None"},
                 "Саратов": {"UF_CRM_1723401598955": 'None'},
                 "Энгельс": {"UF_CRM_1722889900952": 'None'},
                 "Улица": {"UF_CRM_1722889043533": "None"},
                 "Оплата": {"UF_CRM_1722890070498": 'None'},
                 "Начало работ ": {"UF_CRM_1722890021769": 'None'}}
    order_dict = {**contact_dict, **deal_dict}
    result = requests.get(f'{config.tg_bot.bitrix}/crm.deal.get?id={id_deal}').json()
    if 'error' in result.keys():
        return "No_deal"
    deal: dict = requests.get(f'{config.tg_bot.bitrix}/crm.deal.get?id={id_deal}').json()['result']
    # print(deal)
    field_deal: dict = requests.get(f'{config.tg_bot.bitrix}/crm.deal.fields?id=30').json()['result']
    # print(field_deal)
    result: dict = requests.get(f'{config.tg_bot.bitrix}/crm.contact.get?id={deal["CONTACT_ID"]}').json()
    if 'error' in result.keys():
        return 'No_contact'
    else:
        contact: dict = requests.get(f'{config.tg_bot.bitrix}/crm.contact.get?id={deal["CONTACT_ID"]}').json()['result']
    for key, value in contact.items():
        for k, v in order_dict.items():
            temp = list(v.keys())
            if temp[0] == key:
                if key != 'PHONE':
                    if contact[key]:
                        order_dict[k][temp[0]] = contact[key]
                else:
                    order_dict[k][temp[0]] = contact[key][0]['VALUE']

    for key, value in deal.items():
        for k, v in order_dict.items():
            temp = list(v.keys())
            if temp[0] == key:
                if key != 'UF_CRM_1723401519885' and key != 'UF_CRM_1722889043533':
                    for i in field_deal[key]['items']:
                        if i['ID'] == deal[key]:
                            order_dict[k][temp[0]] = i['VALUE']
                else:
                    order_dict[k][temp[0]] = deal[key]
    # print(order_dict)
    return order_dict


if __name__ == '__main__':
    # id_deal = int(input('Пришлите номер заявки: '))
    asyncio.run(get_data_deal(id_deal=128))
