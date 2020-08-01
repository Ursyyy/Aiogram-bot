import mysql.connector
from random import randint
from threading import Thread
from . import work_with_google
from . import get_telegram_user_info

mydb = mysql.connector.connect(
	host="host",
	user="user",
	passwd="pasword",
	database="database"
)

HOW_MANY_SCROLLS = 10

cursor = mydb.cursor(buffered=True)

def EventList() -> list:
	cursor.execute("SELECT eventID, Title FROM events")
	return cursor.fetchall()

def Categories() -> list:
	cursor.execute("SELECT categoryName FROM categories")
	return cursor.fetchall()

def GetFirstEvent(categoryName:str = "") -> list:
	if categoryName == "":
		cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription from events LIMIT %s", (HOW_MANY_SCROLLS,))
	else:
		cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription from events WHERE Category = %s LIMIT %s", (categoryName, HOW_MANY_SCROLLS))
	return cursor.fetchall()

def CheckIsActive(eventID:int, username:str) -> bool:
	cursor.execute("SELECT refcodeStatus FROM refcodes WHERE eventID = %s AND userTelUsername = %s", (eventID, username))
	res = cursor.fetchone()
	if not(res is None):
		return res[0] == "inactive"
	return True

def GetEventInfo(eventID:int) ->tuple:
	cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventID = %s",(eventID,))
	return cursor.fetchone()
	
def GetNextEvent(eventID:int, categoryName:str = "") ->list:
	if categoryName == "":
		cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription FROM events WHERE eventID > %s LIMIT %s", (eventID, HOW_MANY_SCROLLS))
	else:
		cursor.execute(f"SELECT eventID, PictureURL, Title, ShortDescription from events WHERE Category = %s and eventID > {eventID} LIMIT %s", (categoryName, HOW_MANY_SCROLLS))
	return cursor.fetchall()

def GetPrevEvent(eventID:int, categoryName:str = "") ->list:
	if categoryName == "":
		cursor.execute(f"SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventID < {eventID} ORDER BY eventID DESC LIMIT %s", (HOW_MANY_SCROLLS, ))
	else:
		cursor.execute(f"SELECT eventID, PictureURL, Title, ShortDescription from events WHERE Category = %s and eventID < {eventID} ORDER BY eventID DESC LIMIT %s", (categoryName, HOW_MANY_SCROLLS))
	return cursor.fetchall()

def MaxRefCode() -> int:
	cursor.execute(f"SELECT userrefcode FROM refcodes ORDER BY userrefcode DESC LIMIT 0,1")
	codes = cursor.fetchall()
	if codes == []:
		return 0
	return codes[0][0]

def AvailabilityRefCode(eventId: int, userTelUsername: int) -> int:
	cursor.execute(f"SELECT userrefcode FROM refcodes WHERE eventID = %s AND userTelUsername = %s", (eventId, userTelUsername))
	result = cursor.fetchall()
	if result == []:
		return -1
	return result[0][0]

def InsertUserFromRefCode(userTelUsername: str, userRefCode: int, backlink: bool) -> str:
	cursor.execute(f"SELECT * FROM refcodes WHERE userrefcode = {userRefCode}")
	parent_user = cursor.fetchone()
	if parent_user is None:
		return "Неправильный промокод"
	cursor.execute("SELECT userrefcode FROM refcodes WHERE userTelUsername = %s AND eventID = %s", (userTelUsername, parent_user[0]))
	is_correct = cursor.fetchone()
	if not (is_correct is None):
		return "У вас уже есть промокод по данному событию"
	cursor.execute(f"SELECT MaxRefPerDay, MaxRefTotal FROM events WHERE eventID = {parent_user[0]}")
	event = cursor.fetchone()
	if parent_user[7] > event[1] and event[1] != 0:
		return "Пользователь больше не может делиться промокодом по этому событию"
	if parent_user[6] > event[0] and event[0] != 0:
		return "Пользователь больше не может делиться промокодом по этому событию сегодня"
	cursor.execute(f"SELECT recommendedFrom FROM refcodes WHERE userTelUsername = %s AND eventID = %s", (userTelUsername, parent_user[0]))
	user = cursor.fetchone()
	if user is None:
		if backlink: refCode = InsertRefCode(parent_user[0], userTelUsername, shared_from=parent_user[1], refcodeStatus='active')
		else: refCode = InsertRefCode(parent_user[0], userTelUsername)
		if refCode == -1:
			return "Не удалось создать промокод"
		mydb.commit()
		try:
			cursor.execute(f"UPDATE refcodes SET MaxRefTotal = %s , MaxRefPerDay = %s, refcodeStatus = 'active', recommendedFrom = %s WHERE userrefcode = %s", (parent_user[6] + 1, parent_user[7] + 1, parent_user[2], userTelUsername))
			mydb.commit()
		except mysql.connector.Error as error:
			return "Что-то пошло не так, убедитесь в коректности реферального кода"
		return "Вы успешно зарегестрировали промокод"
	return "У вас уже есть рекомендатель по этому событию"

def CreateOrder(eventID:int, userTelUsername:str, orderName:str) -> bool:
	try:
		cursor.execute("UPDATE refcodes SET orderStatus = 'active', orderName = %s WHERE userTelUsername = %s AND eventID", (orderName, userTelUsername, evetID))
		mydb.commit()
		return True
	except:
		return False

def PromocodesList(userTelUsername: str) -> list:
	cursor.execute(f"SELECT eventID, userrefcode FROM refcodes WHERE userTelUsername = %s", (userTelUsername,))
	all_event_by_username = cursor.fetchall()
	result_list = []
	for item in all_event_by_username:
		cursor.execute(f"SELECT Title FROM events WHERE eventID = %s", (item[0],))
		event_title = cursor.fetchone()[0]
		result_list.append((item[1], event_title))
	return result_list

def ActiveOrders(userTelUsername:str) -> list:
	cursor.execute("SELECT eventID, orderName FROM refcodes WHERE orderStatus = 'active' AND userTelUsername = %s",(userTelUsername, ))
	orders = cursor.fetchall()
	result = []
	for order in orders:
		cursor.execute("SELECT Title FROM events WHERE eventID = %s", (order[0], ))
		result.append((cursor.fetchone()[0], order[1]))
	return result

def InsertRefCode(eventId: int, userTelUsername: str, refcodeStatus:str = 'inactive', shared_from:int = None, userSegments:str = "user", MaxRefTotal:int = 0, MaxRefPerDay:int = 0 ) -> int:
	max_code = MaxRefCode()
	if max_code == 0: refCode = randint(200,500)
	else: refCode = max_code + randint(1, 10)
	try:
		cursor.execute(f"""INSERT INTO refcodes (eventID, userTelUsername, userrefcode, refcodeStatus, userSegments,
						recommendedFrom, MaxRefTotal, MaxRefPerDay, orderName, orderStatus)
						VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s )""", (eventId, userTelUsername, refCode, refcodeStatus , userSegments, shared_from, MaxRefTotal, MaxRefPerDay, None, None))
		mydb.commit()
		logs = Thread(target=WriteLogs, args=(userTelUsername,refCode))
		logs.start()
		return refCode
	except:
	   return -1

def WriteLogs(userName:str, refCode:int) -> None:
	user_info = ['Ursyyy', '']
	cursor.execute("SELECT recommendedFrom, refcodeStatus FROM refcodes WHERE userTelUsername = %s AND userrefcode = %s", (userName, refCode,))
	ref_user = cursor.fetchone()
	ref_user_info = ['','','']
	#if not (ref_user is None):
	#    ref_user_info[0] = ref_user
	#    ref_user_info[1], ref_user_info[2] = get_telegram_user_info.GetUserInfo(ref_user)
	cursor.execute("SELECT eventID FROM refcodes WHERE userTelUsername = %s AND userrefcode = %s", (userName, refCode,))
	eventID = cursor.fetchone()[0]
	cursor.execute("SELECT Title FROM events WHERE eventID = %s", (eventID,))
	eventTitle = cursor.fetchone()[0]
	work_with_google.WriteRefCodesToSheets(refCode, userName, eventID, eventTitle, user_info[0], user_info[1], refcodePossibleToUse=ref_user[1], referalUsername=ref_user[0], referalFirstName=ref_user_info[1], refLastName=ref_user_info[2])


