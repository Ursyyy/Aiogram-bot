import logging
from aiogram import Bot, Dispatcher
from functions.config import API_TOKEN

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)