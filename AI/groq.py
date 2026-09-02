from httpx import AsyncClient, Timeout
import asyncio, random, json, filetype
from .chat_manager import ChatManager

# Tried in order for a given key. If a model is deprecated/unavailable (404),
# the next one is tried automatically before giving up on that key.
GROQ_MODELS = [
    'meta-llama/llama-4-scout-17b-16e-instruct',
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant',
]


async def getGroqResponse(chat: ChatManager, key: str, tools: list = None, model_idx: int = 0):
    exExc = ''
    model = GROQ_MODELS[min(model_idx, len(GROQ_MODELS) - 1)]
    try:
        async with AsyncClient(verify=False, follow_redirects=True, timeout=Timeout(connect=10, read=180, write=30, pool=10)) as s:
            r = await s.post("https://api.groq.com/openai/v1/chat/completions", headers={'Authorization': f'Bearer {key}'}, json=dict(
                model=model,
                temperature=1.3, # 0-2
                max_completion_tokens=1024,
                top_p=0.9,
                stream=False,
                stop=None,
                messages=chat.truncated_json(27_000)
            ) | (dict(tools=tools, tool_choice="auto") if tools else dict()))
            if r.status_code == 404 and model_idx < len(GROQ_MODELS) - 1:
                return await getGroqResponse(chat, key, tools, model_idx + 1)
            if r.status_code == 413: exExc = f' Token: {chat.token_count} -'
            rd = random.choice(r.json()['choices'])['message']
            if 'tool_calls' in rd: return rd['tool_calls']
            return rd['content']
    except KeyError: raise Exception(f'Cannot get groq response with key "{key}",{exExc} {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Cannot get groq response with key "{key}",{exExc} {r.status_code} - {r.text}')


async def getGroqStoT(audio: bytes, key: str):
    ft = filetype.guess(audio)
    try:
        async with AsyncClient(verify=False, follow_redirects=True, timeout=Timeout(connect=10, read=180, write=30, pool=10)) as s:
            r = await s.post('https://api.groq.com/openai/v1/audio/transcriptions', headers={'Authorization': f'Bearer {key}'}, data=dict(
                model='whisper-large-v3',
                response_format='json',
            ), files=dict(file=('sample.' + ft.extension, audio, ft.mime)))
            return r.json()['text']
    except KeyError: raise Exception(f'Speech to Text: Cannot get groq response with key "{key}", {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Speech to Text: Cannot get groq response with key "{key}", {r.status_code} - {r.text}')


if __name__ == '__main__':
    api_key = random.choice(json.load(open('api_data.json')).get('groq', []))

    cm = ChatManager()
    cm.addText('user', 'What does this image say?')
    cm.addImages('user', open('image.png', 'rb').read())

    print(asyncio.run(getGroqResponse(cm, api_key)))


