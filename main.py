#
#pip3/pip install aiogram mysql.connector gspread oauth2client telethon
#

from aiogram import executor
import telethon
from aiogram import types
from aiogram.utils.deep_linking import get_start_link
from json import dumps
from concurrent.futures import ThreadPoolExecutor

from functions.sql import *
from bot import bot, dp
from functions.work_with_google import WriteToSQL

#
#time = 11
#

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
	await message.answer("<---   --->")
	splitMsg = message.text.split()
	if len(splitMsg) == 2:
		backlink = False
		try:
			if splitMsg[1].endswith("back"): 
				ref_code = int(splitMsg[1][:-4])
				backlink = True
			else:
				ref_code = int(splitMsg[1])
			await message.answer(InsertUserFromRefCode(message.from_user.username, ref_code, backlink))
		except ValueError:
			await message.answer("Что-то пошло не так, убедитесь в коректности реферального кода")
	elif len(splitMsg) == 1:
		await message.answer("Добро пожаловать, тут вы найдете для себя приятные предложения и возможность заработать")
		await category_list(message)
	else:
		await message.answer("Smth wrong!")

@dp.message_handler(commands=['mypromocodes'])
async def cmd_show_promocodes(message: types.Message):
	await send_promocodes(message)
	await send_active_order(message)

async def send_promocodes(message: types.Message):
	promocode_list = PromocodesList(message.from_user.username)
	if promocode_list != []:
		message_text = "Ваши промокода:\n"
		for data in promocode_list:
			message_text += data[1] + " -- " + str(data[0]) +'\n'
		await message.answer(message_text)
	else: 
		keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text="Найти промокод", callback_data="event_list"))
		await message.answer("У вас сейчас нет промокодов", reply_markup=keyboard)

async def send_active_order(message:types.Message):
	active_orders = ActiveOrders(message.chat.username)
	if active_orders != []:
		await message.answer("<---   --->")
		answer = "Активные заказы:\n"
		for order in active_orders:
			answer += f"{order[0]} -- {order[1]}\n"
		await message.answer(text=answer)

@dp.message_handler(commands=['updatedb'])
async def Update_database(message: types.Message):
	await message.answer("<---   --->")
	await message.answer(text="Подождите, идет обновление таблиц")
	with ThreadPoolExecutor() as executor:
		thread = executor.submit(WriteToSQL)
		await message.answer(thread.result())

@dp.message_handler(commands=['events', "event"])
async def cmd_events(message: types.Message):
	event_split = message.text.split()
	if len(event_split) == 1:
		await category_list(message)
	elif len(event_split) == 2 and event_split[1].lower() == 'all':
		await events_list(message)

async def category_list(message: types.Message):
	cat_list = Categories()
	await message.answer("<---   --->")
	category_keyboard= types.InlineKeyboardMarkup(row_width=3)
	category_keyboard.add(types.InlineKeyboardButton(text="All", callback_data=f"category=all"))
	for category in cat_list:
		category_keyboard.row(types.InlineKeyboardButton(text=category[0].title(), callback_data=f"category={category[0]}"))
	await message.answer(text="Выбери категорию:", reply_markup=category_keyboard)

async def events_list(message: types.Message, category:str = "all"):
	await message.answer("<---   --->")
	if category == "all": eventsData = GetFirstEvent()
	else: eventsData = GetFirstEvent(categoryName=category)
	for data in eventsData:
		await send_event_info(message, data, message.chat.username)
	key1 = types.InlineKeyboardButton(text='➡', callback_data=f"➡={eventsData[0][0]}={eventsData[-1][0]}={category}")
	key2 = types.InlineKeyboardButton(text='⬅', callback_data=f"⬅={eventsData[0][0]}={eventsData[-1][0]}={category}")
	key3 = types.InlineKeyboardButton(text='Выбор категории', callback_data="change_category")
	slide_keyboard = types.InlineKeyboardMarkup(row_width=3)
	slide_keyboard.row(key2, key3, key1)
	await message.answer(text="Переход между страницами", reply_markup=slide_keyboard)

@dp.callback_query_handler(lambda c: c.data)
async def process_callback_btn(callback_query: types.CallbackQuery):
	if callback_query.data.startswith('event_list'):
		await category_list(callback_query.message)

	if callback_query.data == 'change_category':
		await category_list(callback_query.message)

	if callback_query.data.startswith("category="):
		text, category = callback_query.data.lower().split('=')
		await events_list(callback_query.message, category=category)

	if callback_query.data.startswith("activale_promo_event"):
		await bot.send_message(callback_query.from_user.id,text="<---   --->")
		text, eventID, username = callback_query.data.lower().split('=')
		if not CheckIsActive(eventID, username):
			orderName = str(SelectRefCode(eventID, username))+"Order"
			if CreateOrder(eventID, username, orderName):
				await bot.send_message(callback_query.from_user.id,text=f"Создано событие {orderName}. Подождите, скоро с вами свяжется представитель заведения")
			else: await bot.send_message(callback_query.from_user.id,text=f"Возникла ошибка, событие не создано")
		else: 
			code = AvailabilityRefCode(eventID, username)
			share_keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text="Стать реферером", callback_data=f"forward_from_telegram={eventID}={code}"))
			share_keyboard.add(types.InlineKeyboardButton(text="Найти реферера", callback_data=f"forward_from_backlink={eventID}={code}"))
			await bot.send_message(callback_query.from_user.id ,text="Этот промокод у вас пока только для заработка. Для того, чтобы вы могли его использовать, кто-то другой должен заработать за вас. Пригласите друга, дайте ему заработать. А вы получите право и сами использовать этот промокод", reply_markup=share_keyboard)

	if callback_query.data.startswith('generate_from'):
		await bot.send_message(callback_query.from_user.id,text="<---   --->")
		generate_from, event = callback_query.data.split('=')
		username = callback_query.from_user.username
		check_code = AvailabilityRefCode(event, username)
		if check_code == -1:
			code = InsertRefCode(event, username)
			eventInfo = GetEventInfo(event)
			await update_event_info(callback_query.message.message_id, callback_query.message.chat.id, eventInfo, username)
			if code != -1: await bot.send_message(callback_query.from_user.id, text=f"Ваш код: {code}")
			else: await bot.send_message(callback_query.from_user.id, text=f"Что-то пошло не так")
		else:
			await bot.send_message(callback_query.from_user.id, f"У вас уже есть промокод: {check_code}")
	
	if callback_query.data.startswith('forward_from'):
		await bot.send_message(callback_query.from_user.id,text="<---   --->")
		forward_from, event, user_code = callback_query.data.split('=')
		if forward_from == 'forward_from_telegram':
			link = f"t.me/Ursyyy_bot?start={user_code}"#await forward_link_to_telegram(user_code)
			await bot.send_message(callback_query.from_user.id, f"Вот реферальная ссылка, поделитесь ею с другом, чтобы вы могли использовать свой промокод\n\n{link}")
		if forward_from == "forward_from_backlink":
			link = f"t.me/Ursyyy_bot?start={user_code}back"
			await bot.send_message(callback_query.from_user.id, f"Вот реферальная ссылка, поделитесь ею с другом, чтобы вы могли использовать свой промокод\n\n{link}")

	if callback_query.data.startswith('my_purse'):
		await bot.send_message(callback_query.from_user.id,text="<---   --->")
		back_to_events = types.InlineKeyboardMarkup()
		back_button = types.InlineKeyboardButton(text="Найти промокод и заработать", callback_data="event_list")
		back_to_events.add(back_button)
		await bot.send_message(callback_query.from_user.id, text="Тут будет отображаться кошелек", reply_markup=back_to_events)

	if callback_query.data.startswith('➡') or callback_query.data.startswith('⬅'):
		slide_to, eventID_1, eventID_2, category = callback_query.data.split('=')
		if category == "all":
			if slide_to == '➡':	eventsData = GetNextEvent(eventID_2)
			elif slide_to == '⬅': eventsData = GetPrevEvent(eventID_1)
		else: 
			if slide_to == '➡':	eventsData = GetNextEvent(eventID_2, category)
			elif slide_to == '⬅': eventsData = GetPrevEvent(eventID_1, category)
		if eventsData != []:
			chatID = callback_query.message.chat.id
			for data in eventsData:
				await send_event_info_from_callback(chatID, data, callback_query.from_user.username)
			key1 = types.InlineKeyboardButton(text='➡', callback_data=f"➡={eventsData[0][0]}={eventsData[-1][0]}={category}")
			key2 = types.InlineKeyboardButton(text='⬅', callback_data=f"⬅={eventsData[0][0]}={eventsData[-1][0]}={category}")
			key3 = types.InlineKeyboardButton(text='Выбор категории', callback_data=f"change_category")
			keyboard = types.InlineKeyboardMarkup(row_width=3)
			keyboard.row(key2, key3, key1)
			await bot.send_message(chatID, text="Переход между страницами", reply_markup=keyboard)
		else: await bot.answer_callback_query(callback_query.id, text="Вы на крайней странице", show_alert=True)

async def send_event_info(message: types.Message, eventInfo:list, username:str) -> int:
	check_code = AvailabilityRefCode(eventInfo[0], username)
	keyboard = types.InlineKeyboardMarkup()
	if check_code == -1:
		keyboard.add(types.InlineKeyboardButton("Получи код и заработай", callback_data=f"generate_from_event={eventInfo[0]}"))
	else: 
		keyboard.add(types.InlineKeyboardButton("Используй промокод", callback_data=f"activale_promo_event={eventInfo[0]}={username}"))
		keyboard.add(types.InlineKeyboardButton("Поделись и заработай", callback_data=f"forward_from_telegram={eventInfo[0]}={check_code}"))
	keyboard.add(types.InlineKeyboardButton("Мой кошелек", callback_data=f"my_purse={username}"))
	await message.answer_photo(photo=eventInfo[1], caption=f"<b>{eventInfo[2]}</b>\n\n{eventInfo[3]}", reply_markup=keyboard, parse_mode="HTML")

async def send_event_info_from_callback(chatID: int, eventInfo:list, username:str) -> int:
	check_code = AvailabilityRefCode(eventInfo[0], username)
	keyboard = types.InlineKeyboardMarkup()
	if check_code == -1:
		keyboard.add(types.InlineKeyboardButton("Получи код и заработай", callback_data=f"generate_from_event={eventInfo[0]}"))
	else: 
		keyboard.add(types.InlineKeyboardButton("Используй промокод", callback_data=f"activale_promo_event={eventInfo[0]}={username}"))
		keyboard.add(types.InlineKeyboardButton("Поделись и заработай", callback_data=f"forward_from_telegram={eventInfo[0]}={check_code}"))
	keyboard.add(types.InlineKeyboardButton("Мой кошелек", callback_data=f"my_purse={username}"))
	await bot.send_photo(chat_id= chatID ,photo=eventInfo[1], caption=f"<b>{eventInfo[2]}</b>\n\n{eventInfo[3]}", reply_markup=keyboard, parse_mode="HTML")

async def update_event_info(messageId:int, chatID:int, eventInfo:list, username:str):
	check_code = AvailabilityRefCode(eventInfo[0], username)
	keyboard = types.InlineKeyboardMarkup()
	if check_code == -1:
		keyboard.add(types.InlineKeyboardButton("Получи код и заработай", callback_data=f"generate_from_event={eventInfo[0]}"))
	else: 
		keyboard.add(types.InlineKeyboardButton("Используй промокод", callback_data=f"activale_promo_event={eventInfo[0]}={username}"))
		keyboard.add(types.InlineKeyboardButton("Поделись и заработай", callback_data=f"forward_from_telegram={eventInfo[0]}={check_code}"))
	keyboard.add(types.InlineKeyboardButton("Мой кошелек", callback_data=f"my_purse={username}"))
	media_file =dumps({"type":"photo","media": eventInfo[1]})
	await bot.edit_message_media(media=media_file, chat_id=chatID, message_id=messageId)
	await bot.edit_message_caption(chat_id=chatID ,caption=f"<b>{eventInfo[2]}</b>\n\n{eventInfo[3]}", message_id=messageId, reply_markup=keyboard,  parse_mode="HTML")


if __name__ == "__main__":
	executor.start_polling(dp, skip_updates=True)