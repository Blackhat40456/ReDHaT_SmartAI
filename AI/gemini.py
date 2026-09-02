from httpx import AsyncClient, Timeout
import asyncio, random, json, filetype, random
from .chat_manager import ChatManager
from base64 import b64encode

# Tried in order for a given key. If a model is deprecated/unavailable (404),
# the next one is tried automatically before giving up on that key.
GEMINI_MODELS = [
    'gemini-2.5-flash-lite',
    'gemini-2.0-flash-lite',
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-1.5-flash',
]


async def getGeminiResponse(chat: ChatManager, key: str, tools: list = None, n = 0, model_idx: int = 0):
    gemTools = None
    if tools:
        gemTools = [{'functionDeclarations': [t['function'] for t in tools]}]

    model = GEMINI_MODELS[min(model_idx, len(GEMINI_MODELS) - 1)]
    try:
        async with AsyncClient(verify=False, follow_redirects=True, timeout=Timeout(connect=10, read=180, write=30, pool=10)) as s:
            r = await s.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", params=dict(key=key), json=chat.gemini_json | dict(
                generationConfig=dict(
                    temperature=1.3, # 0-2
                    max_output_tokens=1024
                )
            ) | (dict(tools=gemTools) if gemTools else dict()))

            if r.status_code == 404 and model_idx < len(GEMINI_MODELS) - 1:
                return await getGeminiResponse(chat, key, tools, n, model_idx + 1)
            if r.status_code == 500 and n < 5 and tools: return await getGeminiResponse(chat, key, tools, n + 1, model_idx)
            funcResp = []
            for part in r.json()['candidates'][0]['content']['parts']:
                if fc := part.get('functionCall'):
                    funcResp.append(dict(id=f'funcCall_{random.randint(100000, 999999)}', type='function', function=dict(name=fc['name'], arguments=json.dumps(fc['args']))))
            if funcResp: return funcResp
            return '\n'.join(part.get('text', '') for part in r.json()['candidates'][0]['content']['parts'])
    except KeyError: raise Exception(f'Cannot get gemini response with key "{key}", {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Cannot get gemini response with key "{key}", {r.status_code} - {r.text}')


async def getGeminiStoT(audio: bytes, key: str, model_idx: int = 0):
    ft = filetype.guess(audio)
    model = GEMINI_MODELS[min(model_idx, len(GEMINI_MODELS) - 1)]
    try:
        async with AsyncClient(verify=False, follow_redirects=True, timeout=Timeout(connect=10, read=180, write=30, pool=10)) as s:
            r = await s.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", params=dict(key=key), json=dict(
                contents=[dict(
                    role='user',
                    parts=[
                        dict(text='Transcribe this audio file'),
                        dict(inline_data=dict(mime_type=ft.mime, data=b64encode(audio).decode()))
                    ]
                )]
            ))
            if r.status_code == 404 and model_idx < len(GEMINI_MODELS) - 1:
                return await getGeminiStoT(audio, key, model_idx + 1)
            return '\n'.join(part.get('text', '') for part in r.json()['candidates'][0]['content']['parts'])
    except KeyError: raise Exception(f'Speech to Text: Cannot get gemini response with key "{key}", {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Speech to Text: Cannot get gemini response with key "{key}", {r.status_code} - {r.text}')


if __name__ == '__main__':
    api_key = random.choice(json.load(open('api_data.json')).get('gemini', []))

    cm = ChatManager()
    cm.addText('user', 'What does this image say?')
    cm.addImages('user', open('image.png', 'rb').read())

    print(asyncio.run(getGeminiResponse(cm, api_key)))


