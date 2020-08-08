import mysql.connector
from random import randint
from threading import Thread
from . import work_with_google
from . import get_telegram_user_info
from time import sleep
#
#time = 9.5
#

mydb = mysql.connector.connect(
	host="host",
	user="user",
	passwd="pasword",
	database="database",
	charset="utf8mb4"
)

HOW_MANY_SCROLLS = 10
lang = 'en'

cursor = mydb.cursor(buffered=True) 

def Categories() -> list:
	cursor.execute("SELECT categoryName FROM categories")
	return cursor.fetchall()

def GetFirstEvent(categoryName:str = "") -> list:
	if categoryName == "":
		cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventStatus = 'enabled' LIMIT %s", (HOW_MANY_SCROLLS,))
	else:
		cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventStatus = 'enabled' AND Category = %s LIMIT %s", (categoryName, HOW_MANY_SCROLLS))
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
		cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription FROM events WHERE eventStatus = 'enabled' AND eventID > %s LIMIT %s", (eventID, HOW_MANY_SCROLLS))
	else:
		cursor.execute(f"SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventStatus = 'enabled' AND Category = %s and eventID > {eventID} LIMIT %s", (categoryName, HOW_MANY_SCROLLS))
	return cursor.fetchall()

def GetPrevEvent(eventID:int, categoryName:str = "") ->list:
	if categoryName == "":
		cursor.execute(f"SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventStatus = 'enabled' AND eventID < {eventID} LIMIT %s", (HOW_MANY_SCROLLS, ))
	else:
		cursor.execute(f"SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventStatus = 'enabled' AND Category = %s and eventID < {eventID} LIMIT %s", (categoryName, HOW_MANY_SCROLLS))
	return cursor.fetchall()

def MaxRefCode() -> int:
	cursor.execute(f"SELECT userrefcode FROM refcodes ORDER BY userrefcode DESC LIMIT 0,1")
	codes = cursor.fetchall()
	if codes == []:
		return 0
	return codes[0][0]

def GetEventInfo(eventID:int) -> tuple:
	cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription, DetailDescription from events WHERE eventID = %s", (eventID, ))
	return cursor.fetchone()

def SelectRefCode(eventID: int, userTelUsername: str) -> int:
	cursor.execute("SELECT userrefcode FROM refcodes WHERE eventID = %s AND userTelUsername = %s", (eventID, userTelUsername))
	return cursor.fetchone()[0]

def SelectAllRefCode(userTelUsername: str) -> list:
	cursor.execute("SELECT userrefcode, eventID FROM refcodes WHERE userTelUsername = %s", (userTelUsername,))
	ref_codes_and_Title = []
	res = cursor.fetchall()
	for item in res:
		cursor.execute("SELECT Title FROM events WHERE eventID = %s",(item[1],))
		ref_codes_and_Title.append((item[0], cursor.fetchone()[0]))
	return ref_codes_and_Title


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
		return work_with_google.local['TEXT_INCORRECT_CODE'][lang]
	cursor.execute("SELECT userrefcode FROM refcodes WHERE userTelUsername = %s AND eventID = %s", (userTelUsername, parent_user[0]))
	is_correct = cursor.fetchone()
	if not (is_correct is None):
		return work_with_google.local['TEXT_YOU_ALREADY_HAVE_PROMOTIONAL_CODE'][lang]
	cursor.execute(f"SELECT MaxRefPerDay, MaxRefTotal FROM events WHERE eventID = {parent_user[0]}")
	event = cursor.fetchone()
	if parent_user[7] > event[1] and event[1] != 0:
		return work_with_google.local['TEXT_SHARED'][lang]
	if parent_user[6] > event[0] and event[0] != 0:
		return work_with_google.local['TEXT_SHARED_TODAY'][lang]
	cursor.execute(f"SELECT recommendedFrom FROM refcodes WHERE userTelUsername = %s AND eventID = %s", (userTelUsername, parent_user[0]))
	user = cursor.fetchone()
	if user is None:
		if backlink: refCode = InsertRefCode(parent_user[0], userTelUsername, shared_from=parent_user[1], refcodeStatus='active', MaxRefPerDay=1, MaxRefTotal=1, write=False)
		else: refCode = InsertRefCode(parent_user[0], userTelUsername, write=False)
		if refCode == -1:
			return work_with_google.local['TEXT_FAILED_TO_CREATE_CODE'][lang]
		try:
			command = f"UPDATE refcodes SET MaxRefTotal = {parent_user[6] + 1} , MaxRefPerDay = {parent_user[7] + 1}, refcodeStatus = 'active', recommendedFrom = '{userTelUsername}' WHERE userrefcode = { parent_user[2]}"
			cursor.execute(command)
			mydb.commit()
			write = Thread(target=WriteLogs, args=[(parent_user[1], parent_user[0]), (userTelUsername, parent_user[0])])
			write.start()
		except mysql.connector.Error as error:
			return work_with_google.local['TEXT_CODE_ERROR'][lang]
		
		return f"{work_with_google.local['TEXT_SUCCESSFUL_CREATE_CODE'][lang]} {refCode}"
	return work_with_google.local['TEXT_YOU_ALREADY_HAVE_PROMOTIONAL_CODE'][lang]

def CreateOrder(eventID:int, userTelUsername:str, orderName:str) -> bool:
	try:
		cursor.execute("UPDATE refcodes SET orderStatus = 'active', orderName = %s WHERE userTelUsername = %s AND eventID = %s", (orderName, userTelUsername, eventID))
		mydb.commit()
		logs = Thread(target=WriteLogs, args=(userTelUsername,eventID))
		logs.start()
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

def InsertRefCode(eventId: int, userTelUsername: str, refcodeStatus:str = 'inactive', shared_from:int = None, userSegments:str = "user", MaxRefTotal:int = 0, MaxRefPerDay:int = 0, write:bool = True ) -> int:
	max_code = MaxRefCode()
	if max_code == 0: refCode = randint(200,500)
	else: refCode = max_code + randint(1, 10)
	try:
		cursor.execute(f"""INSERT INTO refcodes (eventID, userTelUsername, userrefcode, refcodeStatus, userSegments,
						recommendedFrom, MaxRefTotal, MaxRefPerDay, orderName, orderStatus)
						VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s )""", (eventId, userTelUsername, refCode, refcodeStatus , userSegments, shared_from, MaxRefTotal, MaxRefPerDay, None, None))
		mydb.commit()
		if write:
			logs = Thread(target=WriteLogs, args=([(userTelUsername,eventId)]))
			logs.start()
		return refCode
	except:
	   return -1

def WriteLogs(*args) -> None:
	sleep(1)
	for item in args:
		userName:str = item[0]
		eventID:int = item[1]
		user_info = ['', '']
		cursor.execute("SELECT recommendedFrom, refcodeStatus, orderStatus, orderName FROM refcodes WHERE userTelUsername = %s AND eventID = %s", (userName, eventID,))
		ref_user = cursor.fetchone()
		cursor.execute("SELECT userrefcode FROM refcodes WHERE userTelUsername = %s AND eventID = %s", (userName, eventID,))
		refCode = cursor.fetchone()[0]
		cursor.execute("SELECT Title FROM events WHERE eventID = %s", (eventID,))
		eventTitle = cursor.fetchone()[0]
		work_with_google.WriteRefCodesToSheets(refCode, userName, eventID, eventTitle, user_info[0], user_info[1], refcodePossibleToUse=ref_user[1], referalUsername=ref_user[0], orderStatus=ref_user[2], orderName=ref_user[3])

