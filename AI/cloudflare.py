from httpx import AsyncClient
import asyncio, random, json
from .chat_manager import ChatManager

async def getCloudflareResponse(chat: ChatManager, key: str):
    account_id, key = key.split(':')
    try:
        async with AsyncClient(verify=False, follow_redirects=True) as s:
            r = await s.post(f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-4-scout-17b-16e-instruct", headers={'Authorization': f'Bearer {key}'}, json=dict(
                temperature=.7,
                max_tokens=1024,
                top_p=0.9,
                stream=False,
                stop=None,
                messages=chat.json
            ))
            return r.json()['result']['response']
    except KeyError: raise Exception(f'Cannot get cloudflare response with key "{key}", {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Cannot get cloudflare response with key "{key}", {r.status_code} - {r.text}')


if __name__ == '__main__':
    api_key = random.choice(json.load(open('api_data.json')).get('cloudflare', []))

    cm = ChatManager()
    cm.addText('user', 'What does this image say?')
    cm.addImages('user', open('image.png', 'rb').read())

    print(asyncio.run(getCloudflareResponse(cm, api_key)))


