import mysql.connector
from random import randint
from threading import Thread
import threading
from time import sleep
from datetime import date
from re import split 
from . import work_with_google
from .config import *
#
#time = 10
#	

mydb = mysql.connector.connect(
	host=HOST,
	user=USER,
	passwd=PASSWD,
	database=DATABASE,
	charset=CHARSET
)

cursor = mydb.cursor(buffered=True) 

def CursorConnected() -> None:
	global mydb, cursor
	if not mydb.is_connected():
		mydb = mysql.connector.connect(
			host=HOST,
			user=USER,
			passwd=PASSWD,
			database=DATABASE,
			charset=CHARSET
		)
		cursor = mydb.cursor(buffered=True) 
	mydb.commit()

# def UpdateEventTable():
# 	logs = Thread(target=work_with_google.UpdateEventTable)
# 	logs.start()
# 	logs.join()

def Categories() -> list:
	CursorConnected()
	cursor.execute("SELECT eventID from events")
	for item in cursor.fetchall():
		CheckEventDate(item[0])
	cursor.execute("SELECT categoryName FROM categories")
	categ_tuple = cursor.fetchall()
	categories = []
	for category in categ_tuple:
		categories.append(category[0])
	return categories

def CheckEventIsActive(eventID)->bool:
	cursor.execute("SELECT eventStatus FROM events WHERE eventID = %s", (eventID,))
	status = cursor.fetchone()[0]
	if status == 'disabled' or status == 'closed':
		return False
	return True

def CheckEventDate(eventID:str) -> bool:
	CursorConnected()
	cursor.execute('SELECT EndDate FROM events WHERE eventID = %s',(eventID,))
	try:
		enddate = int('2020'+''.join(cursor.fetchone()[0].split('/')[::-1]))
		cur_date = int(str(date.today()).replace('-',''))
	except: return True
	if cur_date > enddate: 
		try:
			cursor.execute("UPDATE events SET eventStatus = 'disabled' WHERE eventID = %s",(eventID,))
			mydb.commit()
		except: pass
		return False
	return True

def GetFirstEvent(categoryName:str = "") -> list:
	CursorConnected()
	if categoryName == "":
		cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventStatus = 'enabled' LIMIT %s", (HOW_MANY_SCROLLS,))
	else:
		cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventStatus = 'enabled' AND Category = %s LIMIT %s", (categoryName, HOW_MANY_SCROLLS))
	return cursor.fetchall()

def CheckIsActive(eventID:int, username:str) -> bool:
	CursorConnected()
	cursor.execute("SELECT refcodeStatus FROM refcodes WHERE eventID = %s AND userTelUsername = %s", (eventID, username))
	res = cursor.fetchone()
	if not(res is None):
		return res[0] == "inactive"
	return True

def GetEventInfo(eventID:int) ->tuple:
	CursorConnected()
	cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventID = %s",(eventID,))
	return cursor.fetchone()
	
def GetNextEvent(eventID:int, categoryName:str = "") ->list:
	CursorConnected()
	if categoryName == "":
		cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription FROM events WHERE eventStatus = 'enabled' AND eventID > %s LIMIT %s", (eventID, HOW_MANY_SCROLLS))
	else:
		cursor.execute(f"SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventStatus = 'enabled' AND Category = %s and eventID > {eventID} LIMIT %s", (categoryName, HOW_MANY_SCROLLS))
	return cursor.fetchall()

def GetPrevEvent(eventID:int, categoryName:str = "") ->list:
	CursorConnected()
	if categoryName == "":
		cursor.execute(f"SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventStatus = 'enabled' AND eventID < {eventID} LIMIT %s", (HOW_MANY_SCROLLS, ))
	else:
		cursor.execute(f"SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventStatus = 'enabled' AND Category = %s and eventID < {eventID} LIMIT %s", (categoryName, HOW_MANY_SCROLLS))
	return cursor.fetchall()

def MaxRefCode() -> int:
	CursorConnected()
	cursor.execute(f"SELECT userrefcode FROM refcodes ORDER BY userrefcode DESC LIMIT 0,1")
	codes = cursor.fetchall()
	if codes == []:
		return 0
	return codes[0][0]

def GetEventInfo(eventID:int) -> tuple:
	CursorConnected()
	cursor.execute("SELECT eventID, PictureURL, Title, ShortDescription from events WHERE eventID = %s", (eventID, ))
	return cursor.fetchone()

def SelectRefCode(eventID: int, userTelUsername: str) -> int:
	CursorConnected()
	cursor.execute("SELECT userrefcode FROM refcodes WHERE eventID = %s AND userTelUsername = %s", (eventID, userTelUsername))
	return cursor.fetchone()[0]

def SelectAllRefCode(userTelUsername: str) -> list:
	CursorConnected()
	cursor.execute("SELECT userrefcode, eventID FROM refcodes WHERE userTelUsername = %s", (userTelUsername,))
	ref_codes_and_Title = []
	res = cursor.fetchall()
	for item in res:
		cursor.execute("SELECT Title FROM events WHERE eventID = %s",(item[1],))
		ref_codes_and_Title.append((item[0], cursor.fetchone()[0]))
	return ref_codes_and_Title

def AvailabilityRefCode(eventId: int, userTelUsername: int) -> int:
	CursorConnected()
	cursor.execute(f"SELECT userrefcode FROM refcodes WHERE eventID = %s AND userTelUsername = %s", (eventId, userTelUsername))
	result = cursor.fetchall()
	if result == []:
		return -1
	return result[0][0]

def InsertUserFromRefCode(userTelUsername: str, userRefCode: int, backlink: bool, lang:str='ru') -> str:
	CursorConnected()
	
	cursor.execute(f"SELECT * FROM refcodes WHERE userrefcode = {userRefCode}")
	parent_user = cursor.fetchone()
	if parent_user is None:
		return work_with_google.local['TEXT_INCORRECT_CODE'][lang]
	cursor.execute("SELECT userrefcode FROM refcodes WHERE userTelUsername = %s AND eventID = %s", (userTelUsername, parent_user[0]))
	is_correct = cursor.fetchone()
	if not (is_correct is None):
		return work_with_google.local['TEXT_YOU_ALREADY_HAVE_PROMOTIONAL_CODE'][lang]
	cursor.execute('SELECT MaxRefPerDay, MaxRefTotal FROM events WHERE eventID = %s', (parent_user[0],))
	max_ref_per_day, max_ref_total = cursor.fetchone()
	cur_day = date.today()
	cursor.execute("SELECT COUNT(*) FROM refcodes WHERE eventID = %s",(parent_user[0],))
	total = cursor.fetchone()[0]
	cursor.execute("SELECT COUNT(*) FROM refcodes WHERE eventID = %s AND TimeCreate = %s", (parent_user[0], cur_day))
	ref_today = cursor.fetchone()[0]
	if total > max_ref_total and str(max_ref_total) != '0':
		return work_with_google.local['TEXT_SHARED'][lang]
	if ref_today > max_ref_per_day and str(max_ref_per_day) != '0':
		return work_with_google.local['TEXT_SHARED_TODAY'][lang]
	cursor.execute(f"SELECT recommendedFrom FROM refcodes WHERE userTelUsername = %s AND eventID = %s", (userTelUsername, parent_user[0]))
	user = cursor.fetchone()
	if user is None:
		if backlink: refCode = InsertRefCode(parent_user[0], userTelUsername, shared_from=parent_user[1], refcodeStatus='active', write=False)
		else: refCode = InsertRefCode(parent_user[0], userTelUsername, refcodeStatus='active',write=False)
		if refCode == -1:
			return work_with_google.local['TEXT_FAILED_TO_CREATE_CODE'][lang]
		try:
			write = Thread(target=WriteLogs, args=[(parent_user[1], parent_user[0]), (userTelUsername, parent_user[0])])
			write.start()
		except mysql.connector.Error as error:
			return work_with_google.local['TEXT_CODE_ERROR'][lang]
		if backlink: return work_with_google.local['TEXT_SUCCESSFUL_CREATE_BACKCODE'][lang].replace('{var}', str(refCode))
		else: return work_with_google.local['TEXT_SUCCESSFUL_CREATE_CODE'][lang].replace('{var}', str(refCode))
	return work_with_google.local['TEXT_YOU_ALREADY_HAVE_PROMOTIONAL_CODE'][lang]

def MaxOrderKey() -> int:
	CursorConnected()
	cursor.execute(f"SELECT orderKey FROM refcodes ORDER BY orderKey DESC LIMIT 0,1")
	codes = cursor.fetchall()
	if codes == [] or codes[0][0] is None:
		return 0
	return codes[0][0]

def CheckOrder(eventID:int, userTelUsername:str) -> int:
	CursorConnected()
	try:
		cursor.execute('SELECT orderKey FROM refcodes WHERE eventID = %s AND userTelUsername = %s',(eventID, userTelUsername,))
		key= cursor.fetchone()[0]
		if key is None: return -1
		return key
	except:
		pass

def CreateOrder(eventID:int, userTelUsername:str) -> int:
	CursorConnected()
	try:
		maxOrderKey = MaxOrderKey()
		if maxOrderKey != 0: orderKey = int(maxOrderKey) + randint(0,51)
		else: orderKey = randint(100000,100100)
		cursor.execute("UPDATE refcodes SET orderStatus = 'active', orderKey = %s WHERE userTelUsername = %s AND eventID = %s", (orderKey, userTelUsername, eventID))
		mydb.commit()
		logs = Thread(target=WriteOrderToLogs, args=(orderKey, eventID, userTelUsername,'active'))
		logs.start()
		return orderKey
	except:
		return -1

def GetInfoByPromo(code:int)->tuple:
	CursorConnected()
	cursor.execute("SELECT Title, PictureURL, ShortDescription, eventID FROM events WHERE eventID = (SELECT eventID FROM refcodes WHERE userrefcode = %s)", (code,))
	return cursor.fetchone()

def PromocodesList(userTelUsername: str) -> list:
	CursorConnected()
	cursor.execute(f"SELECT eventID, userrefcode FROM refcodes WHERE userTelUsername = %s", (userTelUsername,))
	all_event_by_username = cursor.fetchall()
	result_list = []
	for item in all_event_by_username:
		cursor.execute(f"SELECT Title FROM events WHERE eventID = %s", (item[0],))
		event_title = cursor.fetchone()[0]
		if not CheckEventDate(item[0]):	result_list.append((item[1], -1))
		elif not CheckEventIsActive(item[0]): result_list.append((item[1], -2))
		else: result_list.append((item[1], event_title, item[0]))
	return result_list

def ActiveOrders(userTelUsername:str) -> list:
	CursorConnected()
	cursor.execute("SELECT eventID, orderKey FROM refcodes WHERE orderStatus = 'active' AND userTelUsername = %s",(userTelUsername, ))
	orders = cursor.fetchall()
	result = []
	for order in orders:
		cursor.execute("SELECT Title FROM events WHERE eventID = %s", (order[0], ))
		result.append((cursor.fetchone()[0], order[1]))
	return result

def CloseOrder(orderKey:str):
	CursorConnected()
	cursor.execute('SELECT eventID, userTelUsername FROM refcodes WHERE orderKey = %s',(orderKey,))
	eventID, username = cursor.fetchone()
	cursor.execute("UPDATE refcodes SET orderStatus = null, orderKey = null WHERE orderKey = %s", (orderKey,))
	mydb.commit()
	logs = Thread(target=WriteOrderToLogs, args=(int(orderKey), eventID, username, 'inactive', True))
	logs.start()

def ClosePromocode(code) -> str:
	CursorConnected()
	try:
		cursor.execute("DELETE FROM refcodes WHERE userrefcode = %s", (code,))
		mydb.commit()
		return work_with_google.local['TEXT_DELETE_PROMOCODE']['ru'].replace('{var}', str(code))
	except: return work_with_google.local['TEXT_UNSUCCESS_DELETE']['ru'].replace('{var}', str(code))

def InsertRefCode(eventId: int, userTelUsername: str,  refcodeStatus:str = 'inactive', shared_from:int = None, userSegments:str = "user",  write:bool = True ) -> int:
	CursorConnected()
	max_code = MaxRefCode()
	timeCreate = date.today()
	if max_code == 0: refCode = randint(200,500)
	else: refCode = max_code + randint(1, 10)
	try:
		try: 
			cursor.execute('SELECT orgTelUsername FROM org')
			all_data= cursor.fetchall()
			orgs = []
			for item in all_data:
				orgs.append(item[0])
			if userTelUsername in orgs: 
				refcodeStatus = 'active'
				userSegments = 'org'
		except: pass
		cursor.execute(f"""INSERT INTO refcodes (eventID, userTelUsername, userrefcode, refcodeStatus, userSegments,
						recommendedFrom, TimeCreate, orderStatus,orderKey)
						VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s )""", (eventId, userTelUsername, refCode, refcodeStatus , userSegments, shared_from, timeCreate, None,None))
		mydb.commit()
		if write:
			logs = Thread(target=WriteLogs, args=([(userTelUsername,eventId)]))
			logs.start()
		return refCode
	except Exception as e:
	   print(e)

def WriteLogs(*args) -> None:
	sleep(1)
	for item in args:
		
		userName:str = item[0]
		eventID:int = item[1]
		user_info = ['', '']
		try:
			cursor.execute("SELECT recommendedFrom, refcodeStatus FROM refcodes WHERE userTelUsername = %s AND eventID = %s", (userName, eventID,))
			ref_user = cursor.fetchone()
		except: ref_user = ["", ""]
		try:
			cursor.execute("SELECT userrefcode FROM refcodes WHERE userTelUsername = %s AND eventID = %s", (userName, eventID,))
			refCode = cursor.fetchone()[0]
		except: refCode = ''
		try:
			cursor.execute("SELECT Title FROM events WHERE eventID = %s", (eventID,))
			eventTitle = cursor.fetchone()[0]
		except: eventTitle = ''
		try:
			work_with_google.WriteRefCodesToSheets(refCode, userName, eventID, eventTitle, user_info[0], user_info[1], refcodePossibleToUse=ref_user[1], referalUsername=ref_user[0])
		except: pass

def WriteOrderToLogs(orderKey, eventID, username, orderStatus, closedOrder:bool=False):
	mydb.commit()
	try:
		if not closedOrder:
			cursor.execute('SELECT userrefcode, recommendedFrom FROM refcodes WHERE orderKey = %s ',(orderKey,))
			refcode, recommendedFrom = cursor.fetchone()
		else:
			cursor.execute('SELECT userrefcode, recommendedFrom FROM refcodes WHERE userTelUsername = %s AND eventID = %s',(username,eventID,))
			refcode, recommendedFrom = cursor.fetchone()
		cursor.execute('SELECT Title FROM events WHERE eventID = %s',(eventID,))
		try: Title = cursor.fetchone()[0]
		except: Title = cursor.fetchone()
		work_with_google.WriteRefCodesToSheets(refcode,username,eventID, Title, refcodePossibleToUse='active', referalUsername=recommendedFrom, orderStatus=orderStatus, orderKey=orderKey)
	except: pass
