from httpx import AsyncClient, Timeout
import asyncio, random, json, filetype, random
from .chat_manager import ChatManager
from base64 import b64encode


async def getGeminiResponse(chat: ChatManager, key: str, tools: list = None, n = 0):
    gemTools = None
    if tools:
        gemTools = [{'functionDeclarations': [t['function'] for t in tools]}]
        
    try:
        async with AsyncClient(verify=False, follow_redirects=True, timeout=Timeout(connect=10, read=180, write=30, pool=10)) as s:
            r = await s.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent", params=dict(key=key), json=chat.gemini_json | dict(
                generationConfig=dict(
                    temperature=1.3, # 0-2
                    max_output_tokens=1024
                )
            ) | (dict(tools=gemTools) if gemTools else dict()))

            if r.status_code == 500 and n < 5 and tools: return await getGeminiResponse(chat, key, tools, n + 1)
            funcResp = []
            for part in r.json()['candidates'][0]['content']['parts']:
                if fc := part.get('functionCall'):
                    funcResp.append(dict(id=f'funcCall_{random.randint(100000, 999999)}', type='function', function=dict(name=fc['name'], arguments=json.dumps(fc['args']))))
            if funcResp: return funcResp
            return '\n'.join(part.get('text', '') for part in r.json()['candidates'][0]['content']['parts'])
    except KeyError: raise Exception(f'Cannot get gemini response with key "{key}", {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Cannot get gemini response with key "{key}", {r.status_code} - {r.text}')


async def getGeminiStoT(audio: bytes, key: str):
    ft = filetype.guess(audio)
    try:
        async with AsyncClient(verify=False, follow_redirects=True, timeout=Timeout(connect=10, read=180, write=30, pool=10)) as s:
            r = await s.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent", params=dict(key=key), json=dict(
                contents=[dict(
                    role='user',
                    parts=[
                        dict(text='Transcribe this audio file'),
                        dict(inline_data=dict(mime_type=ft.mime, data=b64encode(audio).decode()))
                    ]
                )]
            ))
            return '\n'.join(part.get('text', '') for part in r.json()['candidates'][0]['content']['parts'])
    except KeyError: raise Exception(f'Speech to Text: Cannot get gemini response with key "{key}", {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Speech to Text: Cannot get gemini response with key "{key}", {r.status_code} - {r.text}')


if __name__ == '__main__':
    api_key = random.choice(json.load(open('api_data.json')).get('gemini', []))

    cm = ChatManager()
    cm.addText('user', 'What does this image say?')
    cm.addImages('user', open('image.png', 'rb').read())

    print(asyncio.run(getGeminiResponse(cm, api_key)))


