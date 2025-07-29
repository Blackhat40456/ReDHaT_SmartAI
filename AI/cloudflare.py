from httpx import AsyncClient, Timeout
import asyncio, random, json
from base64 import b64encode
from .chat_manager import ChatManager

async def getCloudflareResponse(chat: ChatManager, key: str, tools: list = None):
    account_id, key = key.split(':')
    try:
        async with AsyncClient(verify=False, follow_redirects=True, timeout=Timeout(connect=10, read=180, write=30, pool=10)) as s:
            r = await s.post(f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-4-scout-17b-16e-instruct", headers={'Authorization': f'Bearer {key}'}, json=dict(
                temperature=1.3, # 0-5
                max_tokens=1024,
                top_p=0.9,
                stream=False,
                stop=None,
                messages=chat.truncated_json(131_000 - 1024 * 2 - 5e3)
            ) | (dict(tools=tools, tool_choice="auto") if tools else dict()))
            rd = r.json()['result']
            if rd.get('tool_calls') : return rd['tool_calls']
            return rd['response']
    except KeyError: raise Exception(f'Cannot get cloudflare response with key "{key}", {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Cannot get cloudflare response with key "{key}", {r.status_code} - {r.text}')


async def getCloudflareStoT(audio: bytes, key: str):
    account_id, key = key.split(':')
    try:
        async with AsyncClient(verify=False, follow_redirects=True, timeout=Timeout(connect=10, read=180, write=30, pool=10)) as s:
            r = await s.post(f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/openai/whisper-large-v3-turbo", headers={'Authorization': f'Bearer {key}'}, json=dict(
                audio=b64encode(audio).decode(),
                task='transcribe',
            ))
            return r.json()['result']['text']
    except KeyError: raise Exception(f'Speech to Text: Cannot get cloudflare response with key "{key}", {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Speech to Text: Cannot get cloudflare response with key "{key}", {r.status_code} - {r.text}')


if __name__ == '__main__':
    api_key = random.choice(json.load(open('api_data.json')).get('cloudflare', []))

    cm = ChatManager()
    cm.addText('user', 'What does this image say?')
    cm.addImages('user', open('image.png', 'rb').read())

    print(asyncio.run(getCloudflareResponse(cm, api_key)))


