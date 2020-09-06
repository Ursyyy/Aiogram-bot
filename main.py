from aiogram import executor
from aiogram import types
from aiogram.utils.deep_linking import get_start_link
from aiogram.types import InlineQuery, \
	InputTextMessageContent, InlineQueryResultArticle, InlineQueryResultPhoto, InputMediaPhoto
	
import hashlib
import asyncio
from json import dumps
from concurrent.futures import ThreadPoolExecutor
from functions.sql import *
from functions.config import SHARE_LINK
from bot import bot, dp
from functions.work_with_google import WriteToSQL, local, GetLocalData, GetAllLanguages

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
	lang = await GetUserLang(message.from_user.language_code)
	menu_keyboard = await get_menu_keyboard(lang)
	splitMsg = message.text.split()
	if len(splitMsg) == 2:
		backlink = False
		try:
			if splitMsg[1].endswith("back"): 
				ref_code = int(splitMsg[1][:-4])
				backlink = True
			else:
				ref_code = int(splitMsg[1])
			text = InsertUserFromRefCode(message.from_user.username, ref_code, backlink)
			await message.answer(text, reply_markup=menu_keyboard)
			eventInfo = GetInfoByPromo(ref_code)
			await send_event_info(message, [eventInfo[3], eventInfo[1], eventInfo[0], eventInfo[2]], message.chat.username, lang)
		except ValueError:
			await message.answer(local['TEXT_CODE_ERROR'][lang],reply_markup=menu_keyboard)
	elif len(splitMsg) == 1:
		await message.answer(local['TEXT_HELLO'][lang],reply_markup=menu_keyboard)
		await category_list(message)
	else:
		await message.answer("Smth wrong!",reply_markup=menu_keyboard)

@dp.message_handler(commands=['changelang'])
async def cmd_change_lang(message:types.Message): 
	all_languages = await GetAllLanguages()
	msgSplit = message.text.split()
	if len(msgSplit) == 1:
		langs_text = ' '.join(all_languages)
		await message.answer(f"Язык интерфейса: {lang}\n Доступные языки: {langs_text}\n/changelang 'язык' для смены")
	if len(msgSplit) == 2 and msgSplit[1] in all_languages:
		lang = msgSplit[1]
		await message.answer(f"Язык был изменен на {lang}")

@dp.message_handler(commands=['menu'])
async def cmd_menu(message:types.Message):
	lang = await GetUserLang(message.from_user.language_code)
	menu_keyboard = await get_menu_keyboard(lang)
	await message.answer(text=local['TEXT_FOR_MENU'][lang], reply_markup=menu_keyboard)

@dp.message_handler(commands=['mypromocodes'])
async def cmd_show_promocodes(message: types.Message):
	await send_promocodes(message)
	#await send_active_order(message)

async def send_promocodes(message: types.Message):
	lang = await GetUserLang(message.chat.username)
	menu_keyboard = await get_menu_keyboard(lang)
	promocode_list = PromocodesList(message.chat.username)
	if promocode_list != []:
		await message.answer(f"{local['TEXT_PROMOCODES'][lang]}", reply_markup=menu_keyboard)
		for data in promocode_list:
			if data[-1] == -1:
				keyboard =types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text=local['BTN_DELETE_PROMOCODE'][lang], callback_data=f'delete_code={data[0]}'))
				await message.answer(local['TEXT_ENDDATE_EVENT_PROMOCODE'][lang].replace('{var}',str(data[0])), reply_markup=keyboard)
			elif data[-1] == -2:
				keyboard =types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text=local['BTN_DELETE_PROMOCODE'][lang], callback_data=f'delete_code={data[0]}'))
				await message.answer(local['TEXT_STOP_EVENT_PROMOCODE'][lang].replace('{var}',str(data[0])), reply_markup=keyboard)
			else:
				keyboard = await get_promocodes_keyboard(lang, data[2], message.chat.username, data[0])
				keyboard.add(types.InlineKeyboardButton(text=local['BTN_DETAILS'][lang], callback_data=f'details={data[0]}'))
				await message.answer(f"{local['TEXT_YOUR_CODE'][lang]} {data[0]}\n{data[1]}", reply_markup=keyboard)
	else: 
		keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text=local['BTN_TEXT_FIND_CODE'][lang], callback_data="event_list"))
		await message.answer(local['TEXT_NO_PROMOCODES'][lang], reply_markup=keyboard)

async def send_active_order(message:types.Message):
	lang = await GetUserLang(message.chat.username)
	menu_keyboard = await get_menu_keyboard(lang)
	active_orders = ActiveOrders(message.chat.username)
	await message.answer(text=f"{local['TEXT_ACTIVE_ORDERS'][lang]}", reply_markup=menu_keyboard)
	if active_orders != []:
		for order in active_orders:
			keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text=local['BTN_CLOSE_ORDER'][lang], callback_data=f"close_order={order[1]}"))
			await message.answer(text=local['TEXT_ORDER_KEY'][lang].replace('{title}', order[0]) + f'{order[1]}', reply_markup=keyboard)
	else: await message.answer(local['TEXT_NO_ORDERS'][lang])

@dp.message_handler(commands=['updatedb'])
async def Update_database(message: types.Message):
	await message.answer(text="Подождите, идет обновление таблиц")
	await message.answer(WriteToSQL())

@dp.message_handler(commands=['updatelang'])
async def Update_lang(message: types.Message):
	await GetLocalData()
	await message.answer("Язык был обновлен")

@dp.message_handler(commands=['events', "event"])
async def cmd_events(message: types.Message):
	cat_list = Categories()
	event_split = message.text.split()
	if len(event_split) == 1:
		await category_list(message)
	elif len(event_split) == 2 and event_split[1].lower() == 'all':
			await events_list(message)
	elif len(event_split) == 2 and event_split[1].lower() in cat_list:
		await events_list(message, event_split[1].lower())


async def category_list(message: types.Message, lang:str=''):
	if lang == '': lang = await GetUserLang(message.from_user.language_code)
	cat_list = Categories()
	category_keyboard= types.InlineKeyboardMarkup(row_width=3)
	category_keyboard.add(types.InlineKeyboardButton(text=local['BTN_ALL_EVENTS'][lang], callback_data=f"category=all"))
	for category in cat_list:
		category_keyboard.row(types.InlineKeyboardButton(text=category.title(), callback_data=f"category={category}"))
	await message.answer(text=local['TEXT_CHOOSE_CATEGORY'][lang], reply_markup=category_keyboard)

async def events_list(message: types.Message, category:str = "all", lang:str=""):
	if lang == '': lang = await GetUserLang(message.from_user.language_code)
	if category == "all": eventsData = GetFirstEvent()
	else: eventsData = GetFirstEvent(categoryName=category)
	for data in eventsData:
		await send_event_info(message, data, message.chat.username, lang)
	key1 = types.InlineKeyboardButton(text='➡', callback_data=f"➡={eventsData[0][0]}={eventsData[-1][0]}={category}")
	key2 = types.InlineKeyboardButton(text='⬅', callback_data=f"⬅={eventsData[0][0]}={eventsData[-1][0]}={category}")
	key3 = types.InlineKeyboardButton(text=local['BTN_TEXT_CHANGE_CATEGORY'][lang], callback_data="change_category")
	slide_keyboard = types.InlineKeyboardMarkup(row_width=3)
	slide_keyboard.row(key2, key3, key1)
	await message.answer(text=local['TEXT_CHANGE_PAGE'][lang], reply_markup=slide_keyboard)


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def answer_to_menu(message: types.Message):
	lang = await GetUserLang(message.from_user.language_code)
	if message.text.lower() == local['MENU_TEXT_EVENT'][lang].lower(): await category_list(message)
	elif message.text.lower() == local['MENU_TEXT_WALLET'][lang].lower(): await send_promocodes(message)
	elif message.text.lower() == local['MENU_TEXT_ORDER'][lang].lower(): await send_active_order(message)


@dp.callback_query_handler(lambda c: c.data)
async def process_callback_btn(callback_query: types.CallbackQuery):
	if callback_query.data.startswith('event_list'):
		lang = await GetUserLang(callback_query.from_user.language_code)
		await category_list(callback_query.message, lang=lang)
		
	if callback_query.data == 'change_category':
		lang = await GetUserLang(callback_query.from_user.language_code)
		await category_list(callback_query.message, lang=lang)

	if callback_query.data.startswith("category="):
		text, category = callback_query.data.lower().split('=')
		lang = await GetUserLang(callback_query.from_user.language_code)
		await events_list(callback_query.message, category=category, lang=lang)

	if callback_query.data.startswith('details'):
		lang = await GetUserLang(callback_query.from_user.language_code)
		text, code = callback_query.data.split('=')
		eventInfo = GetInfoByPromo(code)
		await send_event_info(callback_query.message, [eventInfo[3], eventInfo[1], eventInfo[0], eventInfo[2]], callback_query.from_user.username, lang)

	if callback_query.data.startswith("activate"):
		lang = await GetUserLang(callback_query.from_user.language_code)
		text, eventID, username = callback_query.data.lower().split('=')
		if not CheckIsActive(eventID, username):
			menu_keyboard = await get_menu_keyboard(lang)
			checkOrder = CheckOrder(eventID, username)
			if checkOrder == -1:
				eventInfo = GetEventInfo(eventID)
				eventText = f"\n\t{eventInfo[2]}\n{eventInfo[3]}"
				orderKey = CreateOrder(eventID, username)
				if orderKey != -1:
					await bot.send_message(callback_query.from_user.id,text=local['TEXT_CREATE_ORDER'][lang].replace('{event}',eventText ).replace('{var}',str(orderKey)), reply_markup=menu_keyboard)
				else: await bot.send_message(callback_query.from_user.id,text=local['TEXT_CREATE_ORDER_ERROR'][lang], reply_markup=menu_keyboard)
			else: 
				await bot.send_message(callback_query.from_user.id,text=local['TEXT_YOUR_ORDER_KEY'][lang]+f'{checkOrder}', reply_markup=menu_keyboard)
		else: 
			code = AvailabilityRefCode(eventID, username)
			share_keyboard = types.InlineKeyboardMarkup()
			share_keyboard.add(types.InlineKeyboardButton(text=local['BTN_FIND_REF'][lang], callback_data=f"forward_from={eventID}={code}back"))
			await bot.send_message(callback_query.from_user.id ,text=local['TEXT_PROMO_ONLY_FOR_EARNING'][lang].replace('{var}', str(code)), reply_markup=share_keyboard)

	if callback_query.data.startswith('generate_from'):
		lang = await GetUserLang(callback_query.from_user.language_code)
		generate_from, event = callback_query.data.split('=')
		username = callback_query.from_user.username
		check_code = AvailabilityRefCode(event, username)
		if check_code == -1:
			code = InsertRefCode(event, username)
			eventInfo = GetEventInfo(event)
			await update_event_info(callback_query.message.message_id, callback_query.message.chat.id, eventInfo, username, lang)
			if code != -1: message_text=f"{local['TEXT_SUCCES_REG_CODE'][lang]}\n\n\t{eventInfo[2]}\n{eventInfo[3]}\n\n{local['TEXT_YOUR_CODE'][lang]} {code}"
			else: message_text=local['TEXT_YOUR_CODE_ERROR'][lang]
		else:
			message_text = f"{local['TEXT_YOU_ALREADY_HAVE_CODE'][lang]} {check_code}"
		keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(local['BTN_TEXT_USE_CODE'][lang], callback_data=f"activate={event}={username}"))
		keyboard.add(types.InlineKeyboardButton(text=local['BTN_TEXT_SHARE_EARN'][lang], callback_data=f"forward_from={event}={code}"))
		keyboard.add(types.InlineKeyboardButton(local['BTN_DELETE_PROMOCODE'][lang], callback_data=f'delete_code={code}'))
		await bot.send_message(callback_query.from_user.id, text=message_text, reply_markup=keyboard)
	
	if callback_query.data.startswith('forward_from'):
		lang = await GetUserLang(callback_query.from_user.language_code)
		forward_from, event, user_code = callback_query.data.split('=')
		if user_code.endswith('back'):
			code = user_code[:-4]
			text = local['TEXT_REF_BACKLINK'][lang]
		else: 
			code = user_code
			text = local['TEXT_REF_LINK'][lang]
		eventInfo = GetInfoByPromo(code)
		link = f"{SHARE_LINK}{user_code}"
		text = text.replace('{var}', code).replace('{event}', eventInfo[0]) + link
		keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text=local['BTN_TEXT_FORWARD_FROM_TG'][lang], switch_inline_query=user_code))
		await bot.send_message(callback_query.from_user.id, text, reply_markup=keyboard)

	if callback_query.data.startswith('delete_code'):
		text, code = callback_query.data.split('=')
		lang = await GetUserLang(callback_query.from_user.language_code)
		menu_keyboard = await get_menu_keyboard(lang)
		await bot.send_message(callback_query.from_user.id,text=ClosePromocode(code), reply_markup=menu_keyboard)

	if callback_query.data.startswith('close_order'):
		lang = await GetUserLang(callback_query.from_user.language_code)
		menu_keyboard = await get_menu_keyboard(lang)
		text, orderKey = callback_query.data.split('=')
		CloseOrder(orderKey)
		await bot.send_message(callback_query.message.chat.id, text=local['TEXT_CLOSE_ORDER'][lang].replace('{var}', orderKey), reply_markup=menu_keyboard)

	if callback_query.data.startswith('my_purse'):
		await cmd_show_promocodes(callback_query.message)

	if callback_query.data.startswith('➡') or callback_query.data.startswith('⬅'):
		lang = await GetUserLang(callback_query.from_user.language_code)
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
				await send_event_info_from_callback(chatID, data, callback_query.from_user.username, lang)
			key1 = types.InlineKeyboardButton(text='➡', callback_data=f"➡={eventsData[0][0]}={eventsData[-1][0]}={category}")
			key2 = types.InlineKeyboardButton(text='⬅', callback_data=f"⬅={eventsData[0][0]}={eventsData[-1][0]}={category}")
			key3 = types.InlineKeyboardButton(text=local['BTN_TEXT_CHANGE_CATEGORY'][lang], callback_data=f"change_category")
			keyboard = types.InlineKeyboardMarkup(row_width=3)
			keyboard.row(key2, key3, key1)
			await bot.send_message(chatID, text=local['TEXT_CHANGE_PAGE'][lang], reply_markup=keyboard)
		else: await bot.answer_callback_query(callback_query.id, text=local['TEXT_LAST_PAGE'][lang], show_alert=True)

async def send_event_info(message: types.Message, eventInfo:list, username:str, lang:str) -> int:
	check_code = AvailabilityRefCode(eventInfo[0], username)
	keyboard = types.InlineKeyboardMarkup()
	if check_code == -1:
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_GET_CODE'][lang], callback_data=f"generate_from_event={eventInfo[0]}"))
	else: 
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_USE_CODE'][lang], callback_data=f"activate={eventInfo[0]}={username}"))
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_SHARE_EARN'][lang], callback_data=f"forward_from={eventInfo[0]}={check_code}"))
		keyboard.add(types.InlineKeyboardButton(local['BTN_DELETE_PROMOCODE'][lang], callback_data=f'delete_code={check_code}'))

	#.add(types.InlineKeyboardButton(local['BTN_MY_WALLET'][lang], callback_data=f"my_purse={username}"))
	await message.answer_photo(photo=eventInfo[1], caption=f"<b>{eventInfo[2]}</b>\n\n{eventInfo[3]}", reply_markup=keyboard, parse_mode="HTML")

async def send_event_info_from_callback(chatID: int, eventInfo:list, username:str, lang:str) -> int:
	check_code = AvailabilityRefCode(eventInfo[0], username)
	keyboard = types.InlineKeyboardMarkup()
	if check_code == -1:
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_GET_CODE'][lang], callback_data=f"generate_from_event={eventInfo[0]}"))
	else: 
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_USE_CODE'][lang], callback_data=f"activate={eventInfo[0]}={username}"))
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_SHARE_EARN'][lang], callback_data=f"forward_from={eventInfo[0]}={check_code}"))
		keyboard.add(types.InlineKeyboardButton(local['BTN_DELETE_PROMOCODE'][lang], callback_data=f'delete_code={check_code}'))
	#keyboard.add(types.InlineKeyboardButton(local['BTN_MY_WALLET'][lang], callback_data=f"my_purse={username}"))
	await bot.send_photo(chat_id= chatID ,photo=eventInfo[1], caption=f"<b>{eventInfo[2]}</b>\n\n{eventInfo[3]}", reply_markup=keyboard, parse_mode="HTML")

async def update_event_info(messageId:int, chatID:int, eventInfo:list, username:str, lang:str):
	check_code = AvailabilityRefCode(eventInfo[0], username)
	keyboard = types.InlineKeyboardMarkup()
	if check_code == -1:
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_GET_CODE'][lang], callback_data=f"generate_from_event={eventInfo[0]}"))
	else: 
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_USE_CODE'][lang], callback_data=f"activate={eventInfo[0]}={username}"))
		keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_SHARE_EARN'][lang], callback_data=f"forward_from={eventInfo[0]}={check_code}"))
		keyboard.add(types.InlineKeyboardButton(local['BTN_DELETE_PROMOCODE'][lang], callback_data=f'delete_code={check_code}'))
	media_file =dumps({"type":"photo","media": eventInfo[1]})
	await bot.edit_message_media(media=media_file, chat_id=chatID, message_id=messageId)
	await bot.edit_message_caption(chat_id=chatID ,caption=f"<b>{eventInfo[2]}</b>\n\n{eventInfo[3]}", message_id=messageId, reply_markup=keyboard,  parse_mode="HTML")

async def get_menu_keyboard(lang:str):
	menu_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False, selective=True)
	menu_keyboard.add(types.KeyboardButton(local['MENU_TEXT_EVENT'][lang]),types.KeyboardButton(local['MENU_TEXT_WALLET'][lang]),types.KeyboardButton(local['MENU_TEXT_ORDER'][lang]))
	return menu_keyboard

async def get_promocodes_keyboard(lang:str, eventID: int, username:str, code: int):
	keyboard = types.InlineKeyboardMarkup()
	keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_USE_CODE'][lang], callback_data=f"activate={eventID}={username}"))
	keyboard.add(types.InlineKeyboardButton(local['BTN_TEXT_SHARE_EARN'][lang], callback_data=f"forward_from={eventID}={code}"))
	keyboard.add(types.InlineKeyboardButton(local['BTN_DELETE_PROMOCODE'][lang], callback_data=f'delete_code={code}'))
	return keyboard

@dp.inline_handler()
async def inline_echo(inline_query: InlineQuery):
	text = inline_query.query or ''
	username = inline_query.from_user.username
	events_with_ref_code = SelectAllRefCode(username)
	items = []
	for item in events_with_ref_code:
		if text == '' or text == ' ':
			eventInfo = GetInfoByPromo(item[0])
			result_id: str = hashlib.md5(str(item[0]).encode()).hexdigest()
			if str(item[0]).endswith('back'): text = f"{local['TEXT_SHARE_BY_TG_BACK']['ru'] }\n\n{eventInfo[0]}\n{eventInfo[2]}\n\n{local['TEXT_SHARE_BY_TG_LINK']['ru']}\n<a href='{SHARE_LINK}{item[0]}back'>Использовать промокод</a>"
			else: text = f"{local['TEXT_SHARE_BY_TG']['ru']}\n\n{eventInfo[0]}\n{eventInfo[2]}\n\n{local['TEXT_SHARE_BY_TG_LINK']['ru']}\n<a href='{SHARE_LINK}{item[0]}'>Использовать промокод</a>" 		
			input_content = InputTextMessageContent(message_text=text, parse_mode="HTML")		
			items.append(InlineQueryResultArticle(
					id=result_id,
					thumb_url=eventInfo[1],
					description=f'Событие: {item[1]}',
					input_message_content=input_content,
					title=f'Промокод: {item[0]}',
				))		
		else:
			if str(item[0]).startswith(text[:3]):
				eventInfo = GetInfoByPromo(item[0])
				result_id: str = hashlib.md5(str(item[0]).encode()).hexdigest()
				if text.endswith('back'): text = f"{local['TEXT_SHARE_BY_TG_BACK']['ru'] }\n\n{eventInfo[0]}\n{eventInfo[2]}\n\n{local['TEXT_SHARE_BY_TG_LINK']['ru']}\n<a href='{SHARE_LINK}{item[0]}back'>Использовать промокод</a>"
				else: text = f"{local['TEXT_SHARE_BY_TG']['ru']}\n\n{eventInfo[0]}\n{eventInfo[2]}\n\n{local['TEXT_SHARE_BY_TG_LINK']['ru']}\n<a href='{SHARE_LINK}{item[0]}'>Использовать промокод</a>" 		
				input_content = InputTextMessageContent(message_text=text, parse_mode="HTML")		
				items.append(InlineQueryResultArticle(
					id=result_id,
					thumb_url=eventInfo[1],
					description=f'Событие: {item[1]}',
					input_message_content=input_content,
					title=f'Промокод: {item[0]}',
				))	
	await bot.answer_inline_query(inline_query.id, results=items, cache_time=1)

async def GetUserLang(lang:str):
	#all_languages = await GetAllLanguages()
	#if lang in all_languages: return lang
	return 'ru'

asyncio.run(GetLocalData())

executor.start_polling(dp, skip_updates=True)