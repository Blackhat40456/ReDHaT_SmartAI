from pyrogram import Client, filters
from pyrogram.types import Message as MessageType
from pyrogram.enums import ChatAction
from AI import ChatManager, getAIResponse
from contextlib import asynccontextmanager
from sentence_splitter import split
from web import app
import io, asyncio, random, json
import nest_asyncio
nest_asyncio.apply()


MAX_USER_MSG = 20
REDHAT_SESSION = "BQFYoXsAcpzdShVK7yYw4yQv-sBORcN1XEW3RcZOmGu9gHCebk8qOqcedpqkBsETZycsPa77qudni7PfrI_whTZgvU-GRykNaKsHozKQRsgWK8puPARpK9HBE8nqBLDN4MoUjnXeGv4FhNp5U7rlTJ1Wm8eBGuHbocNilPFoWmNHqZhC2Y_eXpBsmVXxy183jG7bnaJEMXLDUzG20-J8vMAL03n3AKKVtYkCgYFstAMAQtgejR-AEm50oubEYbYkV8j02dD9PuxD6f9E8Tioce2L2KmrhTfFZxcKbvBIp51Mk9csOIxmNWkivYtOtpU1PIf3GBbgjRwhuquSYKyGiTBBR7B69gAAAAFXwLNAAA"
LUCKY_SESSION = "BQGNedwAdo4zugl9OB9kVuwumjx_3edEtAyXx481YKk-WRqBloxL4RuH4EM4r-ML5UNArQkk-spHTpMbKu958kjSUTwzNtoUZSVlA6gkL9vxxxGyoR8pd-l7wLEG6eMmMXETfqU96_d_aEKicDZTBzQT0qSi53j58taTOfusFlZphRl2kj2E4pU5zv4Z4xnY2m_lOpH5N4RfTdYTX68pb3EEppogEyFW1xY7LFLogUdooCyDaOHE2R4hrFEqj1CXQLk6EMyPQAZhdl78ViDB2mcVJN-Om5F0Za1YQXhVSGhc2KXF70QNysFskABal6zIjGuOvJwdsiLa8JMPxEWmCU40EZlTiwAAAAHOVTs6AA"
bot = Client('ReDHaT', 26048988, "cbe8e0074a0c1c6ff38fe30284f5914e", session_string=REDHAT_SESSION)


Settings = lambda: app.config['AI_SETTINGS']
ApiKeys = lambda: app.config['AI_API_KEYS']
IgnoreList = lambda: app.config['AI_IGNORE_LIST']

if False:
    json.dump(dict(s=Settings(), a=ApiKeys(), i=IgnoreList()), open('data.json', 'w'), indent=4)
    print('Data Saved Successfully.')
    exit()

# data = json.load(open('data.json'))
# Settings = lambda: data['s']
# ApiKeys = lambda: data['a']
# IgnoreList = lambda: data['i']

PENDING_MESSAGES = dict()


@bot.on_message(filters.private & ~filters.me & ~filters.bot)
async def handle_user_message(client: Client, message: MessageType):
    uid = message.from_user.id
    username = message.from_user.username
    name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}"
    if not Settings()['enabled']: return
    if not any([message.text, message.voice, message.photo, message.caption, message.audio]): return
    if uid in IgnoreList() or username in IgnoreList(): return
    if message.forward_from and message.forward_from.is_bot: return

    try: message.text = f'My uid is {str(int(message.text))}'
    except ValueError: pass
    except TypeError: pass

    rand = random.random()
    PENDING_MESSAGES[uid] = rand
    await asyncio.sleep(random.randint(7, 15))
    if PENDING_MESSAGES[uid] != rand: return
    await client.read_chat_history(uid)
    await asyncio.sleep(random.randint(2, 6))
    if PENDING_MESSAGES[uid] != rand: return

    cm = ChatManager(Settings()['prompt'] + f'\n\nUser\'s Account Name is "{name}"', ApiKeys())
    all_msgs: list[MessageType] = []
    user_msg_count = 0
    img_count = 0

    async with typing_status(message):
        async for msg in client.get_chat_history(uid, 40):
            if msg and any([message.text, message.photo, message.audio, message.caption, message.voice]):
                if msg.from_user and msg.from_user.id == uid:
                    user_msg_count += 1
                all_msgs.append(msg)
                if user_msg_count >= MAX_USER_MSG:
                    break
        
        for msg in reversed(all_msgs):
            role = 'user' if msg.from_user and msg.from_user.id == uid else 'assistant'
            if t := msg.text or msg.caption:
                if reply_id := msg.reply_to_message_id:
                    reply_msg = next((mg for mg in all_msgs if mg.id == reply_id), None)
                    if reply_msg and reply_msg.text:
                        t = f'I say: "{t}"\nReplying to {"my" if reply_msg.from_user and reply_msg.from_user.id == uid else "your"} message: "{reply_msg.text}"'
                if msg.forward_from:
                    t = f'Forwarded: "{t}"'
                cm.addText(role, t)
            if msg.photo and img_count < 4:
                img_data: io.BytesIO = await msg.download(in_memory=True)
                img_bytes = img_data.getvalue()
                await cm.addImages(role, img_bytes)
                img_count += 1
            if msg.audio or msg.voice:
                audio_data: io.BytesIO = await msg.download(in_memory=True)
                audio_bytes = audio_data.getvalue()
                await cm.addAudio(role, audio_bytes)

        
        if PENDING_MESSAGES[uid] != rand: return
        reply = await getAIResponse(cm, ApiKeys(), client)
        reply = (reply or "").strip() or "I'm busy right now..."
        if PENDING_MESSAGES[uid] != rand: return
        for i, r in enumerate(split(reply)):
            if i != 0: await asyncio.sleep(random.randint(2, 7))
            await message.reply_text(r)


@asynccontextmanager
async def typing_status(message: MessageType):
    running = True

    async def keep_typing():
        while running:
            await message.reply_chat_action(ChatAction.TYPING)
            await asyncio.sleep(2)
        await message.reply_chat_action(ChatAction.CANCEL)

    asyncio.create_task(keep_typing())
    try:
        yield
    finally:
        running = False



bot.run()
