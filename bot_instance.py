import os
from itertools import product
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())


bot = Bot(
    token=os.getenv('TOKEN'),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

admins_str = os.getenv('ADMIN_LIST')
# Проверка, что переменная не пуста, и создание списка администраторов
if admins_str:
    bot.my_admins_list = [int(admin_id) for admin_id in admins_str.split(',')]
else:
    bot.my_admins_list = []
