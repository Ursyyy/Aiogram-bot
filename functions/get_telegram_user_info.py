from telethon import TelegramClient
from telethon.tl.functions.users import GetFullUserRequest
import asyncio
import telethon.sync

#
#time = .5
#

def GetUserInfo(username:str)->list:
    api_id = 0
    api_hash = "LoL"
    client = TelegramClient('getUserInfo', api_id, api_hash)
    client.start()
    full = client(GetFullUserRequest(username))
    print(full)
    first_name = full.user.first_name if not (full.user.first_name is None) else " "
    last_name = full.user.last_name if not (full.user.last_name is None) else " "

    return [first_name, last_name]

