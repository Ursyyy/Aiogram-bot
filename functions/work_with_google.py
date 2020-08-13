import gspread
import mysql.connector
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

#
#time = 6
#

local = {}


host="localhost"
user="root"
passwd="passwd"
database="db"
charset="utf8mb4"

DATABASE_TABLE = "PayForSay_Database"
LOGS_TABLE = "logs"
ERROR_LOGS_TABLE = "error-logs"

PATH_TO_JSON_FILE = ""

connector = mysql.connector.connect(
	host=host,
	user=user,
	passwd=passwd,
	database=database,
	charset=charset
)

cursor = connector.cursor()

scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(PATH_TO_JSON_FILE, scope)
client = gspread.authorize(creds)
def GetSpreadsheetData(sheetName, worksheetIndex) -> list:   
	try: 
		sheet = client.open(sheetName).get_worksheet(worksheetIndex)	
		lst = sheet.get_all_values()[1:]
		for x in range(len(lst)):
			for y in range(len(lst[x])):
				if lst[x][y] == "":
					lst[x][y] = None
				if type(lst[x][y]) is str and lst[x][y][-1] == '%':
					lst[x][y] = int(lst[x][y][0:-1])
		return lst
	except:
		pass#write_logs.error_logging("Ошибка чтения из Google Sheet")
 
def GetLocalData(sheetName:str="Text_variables") -> dict:  
	global local
	sheet = client.open(sheetName).get_worksheet(0)	
	langs = sheet.get_all_values()[0]
	data = sheet.get_all_values()[1:]
	for x in range(len(data)):
		valiable_name = data[x][0]
		append_data = {}
		for y in range(1,len(data[x])):
			append_data[langs[y]] = data[x][y]
		local[valiable_name] = append_data

def GetAllLanguages(sheetName:str="Text_variables") -> list:
	sheet = client.open(sheetName).get_worksheet(0)	
	return sheet.get_all_values()[0][1:]


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
	cursor.execute("""create table org (orgTellUsername varchar(255), ogrStatus varchar(255), orgName 
		varchar(255), orgSite varchar(255), orgDesc text(1000))""")
	
	for data in org_data:
		cursor.execute(f"""INSERT INTO org (orgTellUsername, ogrStatus, orgName, orgSite, orgDesc)
						VALUES (%s, %s, %s, %S, %s)""", data)
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
		RecreateCompaniesTable()
		RecreateManagersTable()
		RecreateUserTable()
		RecreateOrgTable()	
		RecreateCatTable()	

		return f"Таблицы были обновлены"
	except mysql.connector.Error as error:
		connector.rollback()
		return f"Ошибка: {error}. Таблицы не обновлены"

def WriteRefCodesToSheets(refcode:int ,username:str, eventId:int, eventTitle:str, userFirstName:str ="", userLastName:str ="", refcodePossibleToUse:str ="disable",	referalId:int = "", referalUsername:str = "", orderStatus:str = "", orderName:str =""):
	date, time = str(datetime.today()).split()
	time = time[0:time.find('.')]
	insertData = [date, time, refcode, username, eventId, eventTitle, userFirstName, userLastName, refcodePossibleToUse,	referalId,	referalUsername, orderStatus,	orderName]
	sheet = client.open(LOGS_TABLE)
	
	sheetTitle = 'ref-'+ date[:7]
	try:
		worksheet = sheet.worksheet(sheetTitle)
		last_index = len(worksheet.col_values(1)) + 1
		worksheet.insert_row(insertData, last_index)
		worksheet.add_rows(1)
	except:
		Title = ["Date", "Time", "refcode", "username",	"eventId", "eventTitle", "userFirstName", "userLastName", 
			"refcodePossibleToUse", "referal Id",	"referal username",	"orderStatus", "orderName"]
		worksheet = sheet.add_worksheet(sheetTitle, rows="100", cols="14")
		worksheet = sheet.worksheet(sheetTitle)
		worksheet.insert_row(Title, 1)
		worksheet.insert_row(insertData,2)
		worksheet.add_rows(1)
	
def WriteErrorToSheets(text:str =""):
	date, time = str(datetime.today()).split()
	time = time[0:time.find('.')]
	insertData = [date, time, text]
	sheet = client.open(ERROR_LOGS_TABLE)
	
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
	
