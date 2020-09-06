import gspread
import mysql.connector
import asyncio
import os
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from .config import *

#
# time = 10
#


connector = mysql.connector.connect(
	host=HOST,
	user=USER,
	passwd=PASSWD,
	database=DATABASE,
	charset=CHARSET
)
cursor = connector.cursor(buffered=True)

scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(PATH_TO_JSON_FILE, scope)
client = gspread.authorize(creds)


def CursorConnected() -> None:
	global connector, cursor
	if not connector.is_connected():
		connector = mysql.connector.connect(
			host=HOST,
			user=USER,
			passwd=PASSWD,
			database=DATABASE,
			charset=CHARSET
		)
		cursor = connector.cursor(buffered=True) 


local = {} 
async def GetLocalData(sheetName:str=TEXT_VARIABLES) -> dict:  
	global local
	sheet = client.open_by_key(sheetName).get_worksheet(0)	
	langs = sheet.get_all_values()[0]
	data = sheet.get_all_values()[1:]
	for x in range(len(data)):
		valiable_name = data[x][0]
		append_data = {}
		for y in range(1,len(data[x])):
			append_data[langs[y]] = data[x][y]
		local[valiable_name] = append_data

async def GetAllLanguages(sheetName:str=TEXT_VARIABLES) -> list:
	sheet = client.open_by_key(sheetName).get_worksheet(0)	
	return sheet.get_all_values()[0][1:]

def GetSpreadsheetData(sheetName, worksheetIndex) -> list:   
	try: 
		sheet = client.open_by_key(sheetName).get_worksheet(worksheetIndex)	
		lst = sheet.get_all_values()[1:]
		for x in range(len(lst)):
			for y in range(len(lst[x])):
				if lst[x][y] == "":	lst[x][y] = None
				if type(lst[x][y]) is str and lst[x][y][-1] == '%': lst[x][y] = str(lst[x][y][0:-1])
		return lst
	except:
		pass#write_logs.error_logging("Ошибка чтения из Google Sheet")



def UpdateEventTable():
	events_data = GetSpreadsheetData(DATABASE_TABLE, 0)
	if events_data is None: return
	all_eventid = [int(item[0]) for item in events_data]
	for data in events_data:
		cursor.execute('SELECT * FROM events WHERE eventID = %s', (data[0],))
		cur_event_data = cursor.fetchone()
		for count in range(len(data)):
			try: data[count] = int(data[count])
			except: continue
		try:
			if cur_event_data[0] in all_eventid:
				if not (cur_event_data is None) and list(cur_event_data) != data:
					cursor.execute("""UPDATE events SET eventID = %s, eventStatus = %s, Category = %s, companyID = %s, Region = %s, PictureURL = %s, Video = %s, 
									Title = %s, ShortDescription = %s, DetailDescription = %s, URL = %s, CashBack = %s, CashBacktoReferer = %s, CashBacktoRefererOrg = %s, StartDate = %s, EndDate= %s,
									StartDayOfWeek = %s, EndDayOfWeek = %s, StartHour = %s, EndHour = %s, MaxRefPerDay = %s,  MaxRefTotal = %s WHERE eventID = %s""", data + [data[0]])
					connector.commit()	
				else: continue		
		except:
			cursor.execute(f"""INSERT INTO events (eventID, eventStatus, Category, companyID, Region, PictureURL, Video, 
							Title, ShortDescription, DetailDescription, URL, CashBack, CashBacktoReferer, CashBacktoRefererOrg, StartDate, EndDate,
							StartDayOfWeek, EndDayOfWeek, StartHour, EndHour, MaxRefPerDay,  MaxRefTotal) 
							VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", data)
			connector.commit()

def RecreateEventsTable():
	events_data = GetSpreadsheetData(DATABASE_TABLE, 0)
	cursor.execute("DROP TABLE IF EXISTS events")
	cursor.execute(f"""CREATE TABLE events (eventID BIGINT, eventStatus VARCHAR(10), Category varchar(255),
							companyID INT(255), Region VARCHAR(255), PictureURL VARCHAR(255), Video VARCHAR(255),
							Title VARCHAR(255), ShortDescription TEXT(1000), DetailDescription TEXT(3000), URL VARCHAR(255), 
							CashBack INT(32), CashBacktoReferer INT(32), CashBacktoRefererOrg INT(32), StartDate VARCHAR(255), EndDate VARCHAR(255), StartDayOfWeek VARCHAR(255), 
							EndDayOfWeek VARCHAR(255), StartHour INT(32), EndHour INT(32), MaxRefPerDay INT(128), MaxRefTotal INT(255))""")
	for data in events_data:
		cursor.execute(f"""INSERT INTO events (eventID, eventStatus, Category, companyID, Region, PictureURL, Video, 
							Title, ShortDescription, DetailDescription, URL, CashBack, CashBacktoReferer, CashBacktoRefererOrg, StartDate, EndDate,
							StartDayOfWeek, EndDayOfWeek, StartHour, EndHour, MaxRefPerDay,  MaxRefTotal) 
							VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", data)
	connector.commit()

def RecreateCompaniesTable():
	companies_data = GetSpreadsheetData(DATABASE_TABLE, 1)
	cursor.execute("DROP TABLE IF EXISTS companies")
	cursor.execute("""create table companies (companyID BIGINT unique, companyRegion varchar(255), 
						companyTitle varchar(255), companyShortDescription text(1000), companyDetailDescription 
						text(3000), companyURL varchar(255), companyVerified varchar(255), companyStatus varchar(255))""")
	for data in companies_data:
		cursor.execute(f"""INSERT INTO companies (companyID, companyRegion, companyTitle, companyShortDescription,
						companyDetailDescription, companyURL, companyVerified, companyStatus) VALUES 
						(%s, %s, %s, %s, %s, %s, %s, %s)""", data)	
	connector.commit()

def RecreateManagersTable():
	managers_data = GetSpreadsheetData(DATABASE_TABLE, 2)
	cursor.execute("DROP TABLE IF EXISTS managers")
	cursor.execute("""create table managers (managerID bigint unique, companyID bigint, 
					managerTellUsername varchar(255), managerType varchar(255), managerStatus varchar(255))""")
	for data in managers_data:
		cursor.execute(f"""INSERT INTO managers (managerID, companyID, managerTellUsername, managerType, managerStatus) 
				VALUES (%s, %s, %s, %s, %s)""", data)	
	connector.commit()

def RecreateUserTable():
	usersegments_data = GetSpreadsheetData(DATABASE_TABLE, 3)
	cursor.execute("DROP TABLE IF EXISTS usersegments")
	cursor.execute("""create table userSegments(segmentName varchar(255), tellUsername varchar(255))""")
	for data in usersegments_data:
		cursor.execute(f"""INSERT INTO userSegments(segmentName, tellUsername) VALUES (%s, %s)""", data)
	connector.commit()

def RecreateOrgTable():
	org_data = GetSpreadsheetData(DATABASE_TABLE, 4)
	cursor.execute("DROP TABLE IF EXISTS org")
	cursor.execute("""create table org (orgTelUsername varchar(255), ogrStatus varchar(255), orgName 
		varchar(255), orgSite varchar(255), orgDesc text(1000))""")
	
	for data in org_data:
		cursor.execute(f"""INSERT INTO org (orgTelUsername, ogrStatus, orgName, orgSite, orgDesc)
						VALUES (%s, %s, %s, %s, %s)""", data)
	connector.commit()

def RecreateCatTable():
	cat_data = GetSpreadsheetData(DATABASE_TABLE, 5)
	cursor.execute("DROP TABLE IF EXISTS categories")
	cursor.execute("""create table categories (categoryName varchar(255))""")
	
	for data in cat_data:
		cursor.execute(f"""INSERT INTO categories (categoryName) VALUES (%s)""", (str(data[0]).lower(),))
	connector.commit()
def WriteToSQL() -> str:
	CursorConnected()	
	try:
		RecreateEventsTable()
		try: RecreateCompaniesTable()
		except Exception as e: print(f"1 {e}")
		try: RecreateManagersTable()
		except Exception as e: print(f"2 {e}")
		try: RecreateUserTable()
		except Exception as e: print(f"3 {e}")
		try: RecreateOrgTable()	
		except Exception as e: print(f"4 {e}")
		try: RecreateCatTable()	
		except Exception as e: print(f"5 {e}")

		return f"Таблицы были обновлены"
	except mysql.connector.Error as error:
		connector.rollback()
		return f"Ошибка: {error}. Таблицы не обновлены"

def WriteRefCodesToSheets(refcode:int ,username:str, eventId:int, eventTitle:str, userFirstName:str ="", userLastName:str ="", refcodePossibleToUse:str ="disable",	referalId:int = "", referalUsername:str = "", orderStatus:str = "", orderKey:str="", price=""):
	date, time = str(datetime.today()).split()
	time = time[0:time.find('.')]
	insertData = [date, time, refcode, username, eventId, eventTitle, userFirstName, userLastName, refcodePossibleToUse,	referalId,	referalUsername, orderStatus, orderKey, price]
	sheet = client.open_by_key(LOGS_TABLE)
	
	sheetTitle = 'ref-'+ date[:7]
	try:
		worksheet = sheet.worksheet(sheetTitle)
		last_index = len(worksheet.col_values(1)) + 1
		worksheet.insert_row(insertData, last_index)
		worksheet.add_rows(1)
	except:
		Title = ["Date", "Time", "refcode", "username",	"eventId", "eventTitle", "userFirstName", "userLastName", 
			"refcodePossibleToUse", "referal Id",	"referal username",	"orderStatus", "orderKey", "orderPrice"]
		worksheet = sheet.add_worksheet(sheetTitle, rows="100", cols="14")
		worksheet = sheet.worksheet(sheetTitle)
		worksheet.insert_row(Title, 1)
		worksheet.insert_row(insertData,2)
		worksheet.add_rows(1)
	

def WriteErrorToSheets(text:str =""):
	date, time = str(datetime.today()).split()
	time = time[0:time.find('.')]
	insertData = [date, time, text]
	sheet = client.open_by_key(ERROR_LOGS_TABLE)
	
	sheetTitle = 'Error-'+ date[:7]
	try:
		worksheet = sheet.worksheet(sheetTitle)
		last_index = len(worksheet.col_values(1)) + 1
		worksheet.insert_row(insertData, last_index)
		worksheet.add_rows(1)
	except:
		Title = ["Date", "Time", "Text"]
		worksheet = sheet.add_worksheet(sheetTitle, rows="100", cols="3")
		worksheet = sheet.worksheet(sheetTitle)
		worksheet.insert_row(Title, 1)
		worksheet.insert_row(insertData,2)
		worksheet.add_rows(1)
	

def PostCheckPhoto(file_name:str) -> str:
	
	credentials = service_account.Credentials.from_service_account_file(
			PATH_TO_JSON_FILE , scopes=["https://www.googleapis.com/auth/drive"])
	service = build('drive', 'v3', credentials=credentials)
	file_metadata = {
		'name': file_name,
		'parents': [PHOTO_FOLDER_ID]
	}
	media = MediaFileUpload(PATH_TO_PHOTO_FOLDER +file_name,
							mimetype='image/jpeg',
							resumable=True)
	file = service.files().create(body=file_metadata,
										media_body=media,
										fields='id').execute()
	file_id = file.get('id')
	if not file_id is None:
		return f'https://drive.google.com/file/d/{file_id}/view?usp=sharing'
	return ""

def WriteOrderToSheets(refcode:int ,username:str, eventId:int, eventTitle:str, orderStatus:str = "", orderKey:str="", price=""):
	date, time = str(datetime.today()).split()
	time = time[0:time.find('.')]
	file_name:str = f"Order{orderKey}_Price{price}.jpg"

	try: checkPhoto = PostCheckPhoto(file_name)
	except: checkPhoto = ""
	insertData = [date, time, refcode, username, eventId, eventTitle, orderStatus, orderKey, price, checkPhoto]
	
	
	sheet = client.open_by_key(LOGS_TABLE)
	
	sheetTitle = 'order-'+ date[:7]
	try:
		worksheet = sheet.worksheet(sheetTitle)
		last_index = len(worksheet.col_values(1)) + 1
		worksheet.insert_row(insertData, last_index)
		worksheet.add_rows(1)
	except:
		Title = ["Date", "Time", "refcode", "username",	"eventId", "eventTitle", "orderStatus", "orderKey", "orderPrice", 'checkPhoto']
		worksheet = sheet.add_worksheet(sheetTitle, rows="100", cols="14")
		worksheet = sheet.worksheet(sheetTitle)
		worksheet.insert_row(Title, 1)
		worksheet.insert_row(insertData,2)
		worksheet.add_rows(1)
	os.remove(PATH_TO_PHOTO_FOLDER+file_name)

