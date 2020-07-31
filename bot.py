import logging
from aiogram import Bot, Dispatcher

API_TOKEN = "YOUR_TOKEN"
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)