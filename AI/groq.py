from httpx import AsyncClient
import asyncio, random, json
from .chat_manager import ChatManager

async def getGroqResponse(chat: ChatManager, key: str):
    try:
        async with AsyncClient(verify=False, follow_redirects=True) as s:
            r = await s.post("https://api.groq.com/openai/v1/chat/completions", headers={'Authorization': f'Bearer {key}'}, json=dict(
                model='meta-llama/llama-4-scout-17b-16e-instruct',
                temperature=.7,
                max_completion_tokens=1024,
                top_p=0.9,
                stream=False,
                stop=None,
                messages=chat.json
            ))
            return random.choice(r.json()['choices'])['message']['content']
    except KeyError: raise Exception(f'Cannot get groq response with key "{key}", {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Cannot get groq response with key "{key}", {r.status_code} - {r.text}')


if __name__ == '__main__':
    api_key = random.choice(json.load(open('api_data.json')).get('groq', []))

    cm = ChatManager()
    cm.addText('user', 'What does this image say?')
    cm.addImages('user', open('image.png', 'rb').read())

    print(asyncio.run(getGroqResponse(cm, api_key)))


