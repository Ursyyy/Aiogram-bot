#
#pip3/pip install aiogram mysql.connector gspread oauth2client telethon
#
from aiogram import executor
import telethon
from aiogram import types
from aiogram.utils.deep_linking import get_start_link
from json import dumps
from concurrent.futures import ThreadPoolExecutor
from functions.locale import *
from functions.sql import *
from bot import bot, dp
from functions.work_with_google import WriteToSQL, local, GetLocalData, GetAllLanguages

#
#time = 12
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
			await message.answer(local['TEXT_CODE_ERROR'][lang])
	elif len(splitMsg) == 1:
		await message.answer(local['TEXT_HELLO'][lang])
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
		message_text = f"{local['TEXT_PROMOCODES'][lang]}\n"
		for data in promocode_list:
			message_text += data[1] + " -- " + str(data[0]) +'\n'
		await message.answer(message_text)
	else: 
		keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text=local['BTN_TEXT_FIND_CODE'][lang], callback_data="event_list"))
		await message.answer(local['TEXT_NO_PROMOCODES'][lang], reply_markup=keyboard)

async def send_active_order(message:types.Message):
	active_orders = ActiveOrders(message.chat.username)
	if active_orders != []:
		await message.answer("<---   --->")
		answer = f"{local['TEXT_ACTIVE_ORDERS'][lang]}\n"
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
	await message.answer(text=local['TEXT_CHOOSE_CATEGORY'][lang], reply_markup=category_keyboard)

async def events_list(message: types.Message, category:str = "all"):
	await message.answer("<---   --->")
	if category == "all": eventsData = GetFirstEvent()
	else: eventsData = GetFirstEvent(categoryName=category)
	for data in eventsData:
		await send_event_info(message, data, message.chat.username)
	key1 = types.InlineKeyboardButton(text='➡', callback_data=f"➡={eventsData[0][0]}={eventsData[-1][0]}={category}")
	key2 = types.InlineKeyboardButton(text='⬅', callback_data=f"⬅={eventsData[0][0]}={eventsData[-1][0]}={category}")
	key3 = types.InlineKeyboardButton(text=local['BTN_TEXT_CHANGE_CATEGORY'][lang], callback_data="change_category")
	slide_keyboard = types.InlineKeyboardMarkup(row_width=3)
	slide_keyboard.row(key2, key3, key1)
	await message.answer(text=local['TEXT_CHANGE_PAGE'][lang], reply_markup=slide_keyboard)

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
				await bot.send_message(callback_query.from_user.id,text=local['TEXT_CREATE_ORDER'][lang])
			else: await bot.send_message(callback_query.from_user.id,text=local['TEXT_CREATE_ORDER_ERROR'][lang])
		else: 
			code = AvailabilityRefCode(eventID, username)
			share_keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text=local['BTN_BECOME_REF'][lang], callback_data=f"forward_from_telegram={eventID}={code}"))
			share_keyboard.add(types.InlineKeyboardButton(text=local['BTN_FIND_REF'][lang], callback_data=f"forward_from_backlink={eventID}={code}"))
			await bot.send_message(callback_query.from_user.id ,text=local['TEXT_PROMO_ONLY_FOR_EARNING'][lang], reply_markup=share_keyboard)

	if callback_query.data.startswith('generate_from'):
		await bot.send_message(callback_query.from_user.id,text="<---   --->")
		generate_from, event = callback_query.data.split('=')
		username = callback_query.from_user.username
		check_code = AvailabilityRefCode(event, username)
		if check_code == -1:
			code = InsertRefCode(event, username)
			eventInfo = GetEventInfo(event)
			await update_event_info(callback_query.message.message_id, callback_query.message.chat.id, eventInfo, username)
			if code != -1: await bot.send_message(callback_query.from_user.id, text=f"{local['TEXT_YOUR_CODE'][lang]} {code}")
			else: await bot.send_message(callback_query.from_user.id, text=local['TEXT_YOUR_CODE_ERROR'][lang])
		else:
			await bot.send_message(callback_query.from_user.id, f"{local['TEXT_YOU_ALREADY_HAVE_CODE'][lang]} {check_code}")
	if callback_query.data.startswith('forward_from'):
		await bot.send_message(callback_query.from_user.id,text="<---   --->")
		forward_from, event, user_code = callback_query.data.split('=')
		if forward_from == 'forward_from_telegram':
			link = f"t.me/Ursyyy_bot?start={user_code}"#await forward_link_to_telegram(user_code)
			await bot.send_message(callback_query.from_user.id, f"{local['TEXT_REF_LINK'][lang]}\n\n{link}")
		if forward_from == "forward_from_backlink":
			link = f"t.me/Ursyyy_bot?start={user_code}back"
			await bot.send_message(callback_query.from_user.id, f"{local['TEXT_REF_LINK'][lang]}\n\n{link}")

	if callback_query.data.startswith('my_purse'):
		await bot.send_message(callback_query.from_user.id,text="<---   --->")
		back_to_events = types.InlineKeyboardMarkup()
		back_button = types.InlineKeyboardButton(text=local['BTN_FIND_AND_EARN'][lang], callback_data="event_list")
		back_to_events.add(back_button)
		await bot.send_message(callback_query.from_user.id, text=local['TEXT_WALLET'][lang], reply_markup=back_to_events)

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
			key3 = types.InlineKeyboardButton(text=local['BTN_TEXT_CHANGE_CATEGORY'][lang], callback_data=f"change_category")
			keyboard = types.InlineKeyboardMarkup(row_width=3)
			keyboard.row(key2, key3, key1)
			await bot.send_message(chatID, text=local['TEXT_CHANGE_PAGE'][lang], reply_markup=keyboard)
		else: await bot.answer_callback_query(callback_query.id, text=local['TEXT_LAST_PAGE'][lang], show_alert=True)

async def send_event_info(message: types.Message, eventInfo:list, username:str) -> int:
	check_code = AvailabilityRefCode(eventInfo[0], username)
	keyboard = types.InlineKeyboardMarkup()
	if check_code == -1:
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_GET_CODE'][lang], callback_data=f"generate_from_event={eventInfo[0]}"))
	else: 
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_USE_CODE'][lang], callback_data=f"activale_promo_event={eventInfo[0]}={username}"))
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_SHARE_EARN'][lang], callback_data=f"forward_from_telegram={eventInfo[0]}={check_code}"))
	keyboard.add(types.InlineKeyboardButton(local['BTN_MY_WALLET'][lang], callback_data=f"my_purse={username}"))
	await message.answer_photo(photo=eventInfo[1], caption=f"<b>{eventInfo[2]}</b>\n\n{eventInfo[3]}", reply_markup=keyboard, parse_mode="HTML")

async def send_event_info_from_callback(chatID: int, eventInfo:list, username:str) -> int:
	check_code = AvailabilityRefCode(eventInfo[0], username)
	keyboard = types.InlineKeyboardMarkup()
	if check_code == -1:
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_GET_CODE'][lang], callback_data=f"generate_from_event={eventInfo[0]}"))
	else: 
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_USE_CODE'][lang], callback_data=f"activale_promo_event={eventInfo[0]}={username}"))
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_SHARE_EARN'][lang], callback_data=f"forward_from_telegram={eventInfo[0]}={check_code}"))
	keyboard.add(types.InlineKeyboardButton(local['BTN_MY_WALLET'][lang], callback_data=f"my_purse={username}"))
	await bot.send_photo(chat_id= chatID ,photo=eventInfo[1], caption=f"<b>{eventInfo[2]}</b>\n\n{eventInfo[3]}", reply_markup=keyboard, parse_mode="HTML")

async def update_event_info(messageId:int, chatID:int, eventInfo:list, username:str):
	check_code = AvailabilityRefCode(eventInfo[0], username)
	keyboard = types.InlineKeyboardMarkup()
	if check_code == -1:
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_GET_CODE'][lang], callback_data=f"generate_from_event={eventInfo[0]}"))
	else: 
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_USE_CODE'][lang], callback_data=f"activale_promo_event={eventInfo[0]}={username}"))
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_SHARE_EARN'][lang], callback_data=f"forward_from_telegram={eventInfo[0]}={check_code}"))
	keyboard.add(types.InlineKeyboardButton(local['BTN_MY_WALLET'][lang], callback_data=f"my_purse={username}"))
	media_file =dumps({"type":"photo","media": eventInfo[1]})
	await bot.edit_message_media(media=media_file, chat_id=chatID, message_id=messageId)
	await bot.edit_message_caption(chat_id=chatID ,caption=f"<b>{eventInfo[2]}</b>\n\n{eventInfo[3]}", message_id=messageId, reply_markup=keyboard,  parse_mode="HTML")


@dp.inline_handler()
async def inline_echo(inline_query: InlineQuery):
	text = inline_query.query or 0
	username = inline_query.from_user.username
	all_ref_codes = SelectAllRefCode(username)
	if int(text) in all_ref_codes:
		input_content = InputTextMessageContent(message_text=f"<a href='t.me/Ursyyy_bot?start={text}'>Перейти к боту </a>", parse_mode="HTML")
	#else: input_content = InputTextMessageContent("Вы ввели неправильный промокод")
		result_id: str = hashlib.md5(text.encode()).hexdigest()
		item = InlineQueryResultArticle(
		id=result_id,
		title=f'Поделиться промокодом {text!r}',
		input_message_content=input_content,
		)
		await bot.answer_inline_query(inline_query.id, results=[item], cache_time=1)

if __name__ == "__main__":
	GetLocalData()
	executor.start_polling(dp, skip_updates=True)