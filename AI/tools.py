from pyrogram import Client
import asyncio
import nest_asyncio
nest_asyncio.apply()


async def is_uid_verified(bot: Client, uid: int):
    async for msg in bot.search_messages('@ReDHaT4O4_bot', str(uid), limit=1):
        return True
    return False


async def get_deposit_amount(bot: Client, uid: int):
    async for msg in bot.search_messages('@ReDHaT4O4_redep_bot', str(uid), limit=1):
        try: return float(msg.text.strip().split(':')[-1].strip())
        except IndexError: pass
        except TypeError: pass
        except ValueError: pass
    return 0.00


async def check_uid_status(bot: Client, user_id: int, uid: int):
    try: int(uid)
    except ValueError: return "UID must be a number. Ask user to give UID"
    except TypeError: return "UID must be a number. Ask user to give UID"
    if not await is_uid_verified(bot, uid):
        return f'UID ({uid}) is not verified. Registration needed.'
    if (ds := await get_deposit_amount(bot, uid)) < 5:
        return f'UID ({uid}) is not verified because latest deposit is {ds}$ which is less than 5$. More deposit needed.'
    return f'UID ({uid}) is verified and deposit is {ds}$. You are good to go.'
    

async def forward_msg(bot: Client, user_id: int, link: str):
    try:
        lp = link.split('?')[0].split('/')
        cid, mid = lp[3], int(lp[4])
    except: return 'Invalid Message Link, should be like: https://t.me/<slug>/<id>'
    try:
        msg = await bot.get_messages(cid, mid)

        if msg.media_group_id:
            await bot.copy_media_group(user_id, cid, mid)
        else:
            await bot.copy_message(user_id, cid, mid)
        return 'Message Forwarded'
    except Exception as err:
        print(err, flush=True)
        return 'Cannot forward, Internal Error.'


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
    },
    {
        "type": "function",
        "function": {
            "name": forward_msg,
            "description": "Takes a message link, scrapes its content and forwards to user",
            "parameters": {
                "type": "object",
                "properties": {
                    "link": {
                        "type": 'string',
                        "description": "The message link to forward to user. Ex: https://t.me/<slug>/<id>"
                    }
                },
                "required": ["link"]
            }
        }
    }
]

