from pyrogram import Client, filters
from pyrogram.types import Message as MessageType
from AI import ChatManager, getAIResponse
from web import app
import io


bot = Client('ReDHaT', 26048988, "cbe8e0074a0c1c6ff38fe30284f5914e", session_string="BQGNedwAXrdSCFwNITRxHv9G4d7FSP5-7TD9jfM10v_V95Ci4ESjgOk5Wd9n4BFxcypvt_lRwnmfwmquDgGEFuVUblLqwQoZpZ40PFPdqwWQLvAs9aoF0nHq97j0iFCC9mqg95I6JN_TZWB0YFj5vSpOaAquuZKP3pPL_bxtMXfaR_lBmQe8AhPedCsk4y_hTU6RcG1rEikIP8Jc-2cFr2fmgu6nhhLjbzlPW4mU1QgCGqXCKJVXLlyo1eouBhSAiUZUmLWFLQOhm2DFEKLDEVeNf36l66FMrKjuGCOJddojfZnmWntTbHIM6WjYXNnPgbu1C0SLn8P0cl8VVXGB00WOxvG_IgAAAAHOVTs6AA")
Settings = lambda: app.config['AI_SETTINGS']
ApiKeys = lambda: app.config['AI_API_KEYS']
IgnoreList = lambda: app.config['AI_IGNORE_LIST']


@bot.on_message(filters.private & ~filters.me)
async def handle_user_message(client: Client, message: MessageType):
    uid = message.from_user.id
    username = message.from_user.username
    if not Settings()['enabled']: return
    if not any([message.text, message.photo, message.audio, message.caption]): return
    if uid in IgnoreList() or username in IgnoreList(): return
    cm = ChatManager(Settings()['prompt'])
    all_msgs: list[MessageType] = []
    user_msg_count = 0
    await client.read_chat_history(uid)

    async for msg in client.get_chat_history(uid, 40):
        if msg and any([message.text, message.photo, message.audio, message.caption]):
            if msg.from_user and msg.from_user.id == uid:
                user_msg_count += 1
            all_msgs.append(msg)
            if user_msg_count >= 10:
                break
    
    for msg in reversed(all_msgs):
        role = 'user' if msg.from_user and msg.from_user.id == uid else 'assistant'
        if t := msg.text: cm.addText(role, t)
        if cp := msg.caption: cm.addText(role, cp)
        if msg.photo:
            img_data: io.BytesIO = await msg.download(in_memory=True)
            img_bytes = img_data.getvalue()
            await cm.addImages(role, img_bytes)
    
    reply = await getAIResponse(cm, ApiKeys())
    await message.reply_text(reply)



bot.run()
