from fast_bitrix24 import Bitrix
from config_data.config import load_config, Config
import requests
import json
config: Config = load_config()
# замените на ваш вебхук для доступа к Bitrix24
webhook = config.tg_bot.bitrix
bx = Bitrix(webhook)
contact = bx.get_all(method='crm.lead.list')
print(contact)
print(requests.get(f'{config.tg_bot.bitrix}/crm.contact.get?id=1').json()['result'])
# contacts = bx.get_by_ID(
#     'crm.deal.contact.items.get',
#     [c['ID'] for c in contact])
# print(contacts)
# # список сделок в работе, включая пользовательские поля
# deals = bx.get_all(
#     'crm.deal.list',
#     params={
#         'select': ['*', 'UF_*'],
#         'filter': {'CLOSED': 'N'}
# })
# print(deals)
# # print(bx.get_by_ID('crm.deal.contact.items.get'),
# #       [d['ID'] for d in deals])