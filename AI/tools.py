from json import dumps
from pyrogram import Client
import asyncio
import nest_asyncio
nest_asyncio.apply()


async def is_uid_verified(bot: Client, uid: int):
    async for msg in bot.search_messages('@ReDHaT4O4_bot', str(uid), limit=1):
        return True
    return False


async def get_deposit_amount(bot: Client, uid: int):
    total_dep = 0.00
    i = 0
    async for msg in bot.search_messages('@ReDHaT4O4_redep_bot', str(uid)):
        i += 1
        try:
            ck = float(msg.text.strip().split(':')[-1].strip())
            total_dep += ck
            if not ck < 5 and i == 1:
                return ck, False
        except IndexError: pass
        except TypeError: pass
        except ValueError: pass
    return total_dep, True


async def check_uid_status(bot: Client, uid: int):
    note = "The user can either make a single recent deposit of $5 to get verified, or deposit smaller amounts over time that add up to $8 in total."
    try: int(uid)
    except ValueError: return "UID must be a number. Ask user to give UID"
    except TypeError: return "UID must be a number. Ask user to give UID"
    if not await is_uid_verified(bot, uid):
        return f'UID ({uid}) is not verified. Registration needed.'
    ds, is_total = await get_deposit_amount(bot, uid)
    if is_total and ds < 8:
        return f'UID ({uid}) is not verified because "total" deposit is {ds}$ which is less than 8$. More deposit needed. {note}'
    if not is_total and ds < 5:
        return f'UID ({uid}) is not verified because "latest" deposit is {ds}$ which is less than 5$. More deposit needed. {note}'
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

