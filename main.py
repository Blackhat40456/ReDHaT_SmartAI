from pyrogram import Client, filters
from pyrogram.types import Message as MessageType, Dialog as DialogType
from pyrogram.enums import ChatAction, ChatType
from pyrogram.raw import functions, types
from AI import ChatManager, getAIResponse
from AI.memory import (
    extract_facts, facts_from_tool_result, build_memory_block, BEHAVIOR_RULES,
    RETRY_NOTE, is_generic_reply, strip_generic_sentences, fallback_line,
)
from panel.memory_store import load_facts, save_facts
from contextlib import asynccontextmanager
from sentence_splitter import split
from datetime import datetime, timedelta
from web import app
import io, asyncio, random, json, os
import nest_asyncio
nest_asyncio.apply()


MAX_USER_MSG = 20
MAX_IMAGES = 4  # newest N photos from the user are shown to the AI
REDHAT_SESSION = os.environ.get('REDHAT_SESSION')
LUCKY_SESSION = os.environ.get('LUCKY_SESSION')
if not REDHAT_SESSION:
    raise RuntimeError('Missing required environment variable: REDHAT_SESSION must be set in Render.')
bot = Client('ReDHaT', 22585723, "d82628bac795eab81e4b3430819aa026", session_string=REDHAT_SESSION)

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


def _is_from_user(msg: MessageType, uid: int) -> bool:
    return bool(msg.from_user and msg.from_user.id == uid)


def _has_content(msg: MessageType) -> bool:
    return any([msg.text, msg.photo, msg.audio, msg.caption, msg.voice, msg.sticker, msg.animation])


def _normalize_user_text(text) -> str:
    text = (text or '').strip()
    return f'My uid is {text}' if text.isdigit() else text


@bot.on_message(filters.private & ~filters.me & ~filters.bot)
async def handle_user_message(client: Client, message: MessageType, catchup: bool = False):
    uid = message.from_user.id
    username = message.from_user.username
    name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
    if not Settings()['enabled']: return
    if not any([message.text, message.voice, message.photo, message.caption, message.audio, message.video, message.video_note, message.sticker, message.animation]): return
    if uid in IgnoreList() or username in IgnoreList(): return
    fwd_sender = message.forward_origin.sender_user if message.forward_origin else None
    if fwd_sender and fwd_sender.is_bot: return

    try: message.text = f'My uid is {str(int(message.text))}'
    except ValueError: pass
    except TypeError: pass

    rand = random.random()
    PENDING_MESSAGES[uid] = rand
    if not catchup:
        await asyncio.sleep(random.randint(60, 100))
    try:
        await client.read_chat_history(uid)
    except Exception as e:
        print(f"[handle_user_message] read_chat_history failed for {uid} (non-critical, continuing): {e}", flush=True)
    if not catchup:
        await asyncio.sleep(random.randint(20, 40))
    if message.video or message.video_note: return await message.reply_text('💬 Please send videos to my WhatsApp instead of Telegram:https://wa.me/12242268160')
    if await react_if_eligible(message): pass
    if PENDING_MESSAGES[uid] != rand: return

    async with typing_status(message):
        # ---- 1. recent history (newest first, then flipped to chronological) ----
        all_msgs: list[MessageType] = []
        user_msg_count = 0
        async for msg in client.get_chat_history(uid, 40):
            if not msg or not _has_content(msg):
                continue
            if _is_from_user(msg, uid):
                user_msg_count += 1
            all_msgs.append(msg)
            if user_msg_count >= MAX_USER_MSG:
                break
        history = list(reversed(all_msgs))
        has_prior_assistant = any(not _is_from_user(m, uid) for m in history)

        # ---- 2. long-term memory: stored facts + anything new the user said ----
        stored = await asyncio.to_thread(load_facts, uid)
        fresh = {}
        for msg in history:
            if _is_from_user(msg, uid):
                fresh.update(extract_facts(_normalize_user_text(msg.text or msg.caption)))
        facts = {**stored, **fresh}
        if name:
            facts['account_name'] = name
        changed = {k: v for k, v in facts.items() if stored.get(k) != v}
        if changed:
            await asyncio.to_thread(save_facts, uid, changed)

        system_prompt = f"{Settings()['prompt'] or ''}\n\n{build_memory_block(facts)}\n\n{BEHAVIOR_RULES}"
        cm = ChatManager(system_prompt, ApiKeys())
        cm.user_id = uid

        # ---- 3. rebuild the conversation for the AI ----
        user_photo_ids = [m.id for m in history if m.photo and _is_from_user(m, uid)]
        shown_photo_ids = set(user_photo_ids[-MAX_IMAGES:])  # always the NEWEST photos

        for msg in history:
            is_user = _is_from_user(msg, uid)
            role = 'user' if is_user else 'assistant'
            t = msg.text or msg.caption
            if t and is_user:
                t = _normalize_user_text(t)

            if msg.sticker:
                emoji = getattr(msg.sticker, 'emoji', None) or ''
                t = f'[Sticker {emoji}]'.strip()
            elif msg.animation:
                t = '[GIF / animation]'
            elif msg.photo and not t:
                t = '[Photo]' if is_user else '[Photo sent by me]'

            if t:
                if reply_id := msg.reply_to_message_id:
                    reply_msg = next((mg for mg in history if mg.id == reply_id), None)
                    reply_text = reply_msg and (reply_msg.text or reply_msg.caption)
                    if reply_text:
                        t = f'I say: "{t}"\nReplying to {"my" if _is_from_user(reply_msg, uid) else "your"} message: "{reply_text}"'
                if msg.forward_origin:
                    t = f'Forwarded: "{t}"'
                cm.addText(role, t)

            if is_user and msg.photo and msg.id in shown_photo_ids:
                try:
                    img_data: io.BytesIO = await msg.download(in_memory=True)
                    await cm.addImages(role, img_data.getvalue())
                except Exception as e:
                    print(f'[handle_user_message] could not load photo {msg.id}: {e}', flush=True)
                    cm.addText(role, '[Photo that could not be loaded]')
            if is_user and (msg.audio or msg.voice):
                try:
                    audio_data: io.BytesIO = await msg.download(in_memory=True)
                    await cm.addAudio(role, audio_data.getvalue())
                except Exception as e:
                    print(f'[handle_user_message] could not load audio {msg.id}: {e}', flush=True)
                    cm.addText(role, '[Voice message that could not be loaded]')

        if PENDING_MESSAGES[uid] != rand: return

        # ---- 4. ask the AI, and refuse nonsense generic greetings mid-conversation ----
        reply = ((await getAIResponse(cm, ApiKeys(), client)) or '').strip()
        if reply and has_prior_assistant and is_generic_reply(reply):
            cm.addText('system', RETRY_NOTE)
            retry = ((await getAIResponse(cm, ApiKeys(), client)) or '').strip()
            if retry and not is_generic_reply(retry):
                reply = retry
            else:
                kind = 'photo' if message.photo else 'voice' if (message.voice or message.audio) else 'text'
                reply = strip_generic_sentences(reply) or fallback_line(kind)
        reply = reply or "I'm busy right now..."

        # ---- 5. remember what the tools found (e.g. UID verification result) ----
        tool_facts = {}
        for m in cm.messages:
            if m.get('role') == 'tool':
                tool_facts.update(facts_from_tool_result(m.get('content')))
        tool_changed = {k: v for k, v in tool_facts.items() if facts.get(k) != v}
        if tool_changed:
            await asyncio.to_thread(save_facts, uid, tool_changed)

        if PENDING_MESSAGES[uid] != rand: return
        should_quote = random.random() < 0.15  # occasionally reply-to the message for a natural feel, not every time
        for i, r in enumerate(split(reply)):
            if i != 0: await asyncio.sleep(random.randint(2, 7))
            await message.reply_text(r, quote=(should_quote and i == 0))


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


async def react_if_eligible(message: MessageType):
    if not (message.text and len(message.text) < 13 and any(i in message.text.lower() for i in ['ok', 'wait', 'tnx', 'thank', 'welq', 'welc', 'bye', 'night', 'hmm', 'hm'])): return
    await message.react(random.choice(['❤️', '🥰', '😍']))
    return True


async def process_unread_messages():
    """Catch up on unread private DMs — called when AI replying is turned ON
    (from OFF), so messages that piled up while it was off still get a reply,
    no matter how old they are."""
    my_id = (await bot.get_me()).id
    processed = 0
    async for dialog in bot.get_dialogs():
        dialog: DialogType = dialog
        try:
            if dialog.unread_messages_count <= 0: continue
            if dialog.chat.type != ChatType.PRIVATE: continue
            if dialog.chat.id == my_id: continue
            top_msg = dialog.top_message
            if not top_msg or not top_msg.from_user: continue
            if top_msg.from_user.id == my_id: continue  # last message in this chat was already sent by us
            if top_msg.from_user.is_bot: continue

            asyncio.create_task(handle_user_message(bot, top_msg, catchup=True))
            processed += 1
        except Exception as e:
            print(f"[unread_catchup] Error on dialog {getattr(dialog.chat, 'id', '?')}: {e}", flush=True)
    print(f"[unread_catchup] Queued {processed} unread chat(s) for reply.", flush=True)


# async def check_unread(my_id: int):
#     minTime = datetime.now() - timedelta(minutes=15)
#     async for dxx in bot.get_dialogs():
#         dialog: DialogType = dxx
#         isUnread = dialog.unread_messages_count > 0
#         if not isUnread: continue
#         # Manually filtering: filters.private & ~filters.me & ~filters.bot
#         isPrivate = dialog.chat.type == ChatType.PRIVATE
#         if not isPrivate: continue
#         isBot = dialog.chat.type == ChatType.BOT
#         if isBot: continue
#         isMe = dialog.chat.id == my_id
#         if isMe: continue

#         msg = dialog.top_message
#         if msg.from_user.id == my_id: continue
#         if msg.date > minTime: continue
#         asyncio.get_event_loop().create_task(handle_user_message(bot, msg))


async def keepalive():
    while True:
        await asyncio.sleep(60)
        try:
            mp = await bot.get_me()
        except Exception as e:
            print("Error KeepAlive:", e, flush=True)


async def test():
    await bot.start()
    async for i in bot.get_chat_history('allinfobot6'):
        i: MessageType = i
        print(bool(i.photo), bool(i.video), i.text, i.caption, i.media_group_id)
    await bot.stop()

asyncio.get_event_loop().create_task(keepalive())
app.config['BOT_LOOP'] = asyncio.get_event_loop()
app.config['PROCESS_UNREAD'] = process_unread_messages
bot.run()
