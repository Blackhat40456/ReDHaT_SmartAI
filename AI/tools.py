from json import dumps
from pyrogram import Client
import asyncio
import nest_asyncio
nest_asyncio.apply()

UID_CHECK_SESSION_STRING = "BQFYoXsAcpzdShVK7yYw4yQv-sBORcN1XEW3RcZOmGu9gHCebk8qOqcedpqkBsETZycsPa77qudni7PfrI_whTZgvU-GRykNaKsHozKQRsgWK8puPARpK9HBE8nqBLDN4MoUjnXeGv4FhNp5U7rlTJ1Wm8eBGuHbocNilPFoWmNHqZhC2Y_eXpBsmVXxy183jG7bnaJEMXLDUzG20-J8vMAL03n3AKKVtYkCgYFstAMAQtgejR-AEm50oubEYbYkV8j02dD9PuxD6f9E8Tioce2L2KmrhTfFZxcKbvBIp51Mk9csOIxmNWkivYtOtpU1PIf3GBbgjRwhuquSYKyGiTBBR7B69gAAAAFXwLNAAA"
user_main = Client('user_account', api_id=22585723, api_hash='d82628bac795eab81e4b3430819aa026', session_string=UID_CHECK_SESSION_STRING)


async def fn():
    await user_main.start()

asyncio.run(fn())

async def is_uid_verified(uid: int):
    async for msg in user_main.search_messages('@ReDHaT4O4_bot', str(uid), limit=1):
        return True
    return False


async def get_deposit_amount(uid: int):
    async for msg in user_main.search_messages('@ReDHaT4O4_redep_bot', str(uid), limit=1):
        try: return float(msg.text.strip().split(':')[-1].strip())
        except IndexError: pass
        except TypeError: pass
        except ValueError: pass
    return 0.00


async def check_uid_status(uid: int):
    try: int(uid)
    except ValueError: return "UID must be a number. Ask user to give UID"
    except TypeError: return "UID must be a number. Ask user to give UID"
    if not await is_uid_verified(uid):
        return f'UID ({uid}) is not verified. Registration needed.'
    if (ds := await get_deposit_amount(uid)) < 5:
        return f'UID ({uid}) is not verified because deposit is {ds}$ which is less than 5$. More deposit needed.'
    return f'UID ({uid}) is verified and deposit is {ds}$. You are good to go.'
    

tools = [
    {
        "type": "function",
        "function": {
            "name": check_uid_status,
            "description": "Checks if the given UID (basically a number) is verified and account has enough deposit to continue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "uid": {
                        "type": 'string',
                        "description": "The UID to check"
                    }
                },
                "required": ["uid"]
            }
        }
    }
]

