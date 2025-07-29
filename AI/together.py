from httpx import AsyncClient, Timeout
import asyncio, random, json, filetype
from .chat_manager import ChatManager


async def getTogetherResponse(chat: ChatManager, key: str, tools: list = None):
    try:
        async with AsyncClient(verify=False, follow_redirects=True, timeout=Timeout(connect=10, read=180, write=30, pool=10)) as s:
            r = await s.post("https://api.together.xyz/v1/chat/completions", headers={'Authorization': f'Bearer {key}'}, json=dict(
                model='meta-llama/Llama-4-Scout-17B-16E-Instruct',
                temperature=1.3, # 0-2
                max_completion_tokens=1024,
                top_p=0.9,
                stream=False,
                stop=None,
                messages=chat.truncated_json(57_000)
            ) | (dict(tools=tools, tool_choice="auto") if tools else dict()))
            rd = random.choice(r.json()['choices'])['message']
            if rd.get('tool_calls'): return rd['tool_calls']
            return rd['content']
    except KeyError: raise Exception(f'Cannot get together response with key "{key}", {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Cannot get together response with key "{key}", {r.status_code} - {r.text}')
    

async def getTogetherStoT(audio: bytes, key: str):
    ft = filetype.guess(audio)
    try:
        async with AsyncClient(verify=False, follow_redirects=True, timeout=Timeout(connect=10, read=180, write=30, pool=10)) as s:
            r = await s.post("https://api.together.xyz/v1/audio/transcriptions", headers={'Authorization': f'Bearer {key}'}, data=dict(
                model='openai/whisper-large-v3',
                response_format='json',
                language='auto'
            ), files=dict(file=('sample.' + ft.extension, audio, ft.mime)))
            return r.json()['text']
    except KeyError: raise Exception(f'Speech to Text: Cannot get together response with key "{key}", {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Speech to Text: Cannot get together response with key "{key}", {r.status_code} - {r.text}')


if __name__ == '__main__':
    api_key = random.choice(json.load(open('api_data.json')).get('together', []))

    cm = ChatManager()
    cm.addText('user', 'What does this image say?')
    cm.addImages('user', open('image.png', 'rb').read())

    print(asyncio.run(getTogetherResponse(cm, api_key)))


