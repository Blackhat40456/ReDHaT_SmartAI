from httpx import AsyncClient
import asyncio, random, json
from .chat_manager import ChatManager

async def getGeminiResponse(chat: ChatManager, key: str):
    try:
        async with AsyncClient(verify=False, follow_redirects=True) as s:
            r = await s.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite-preview-06-17:generateContent", params=dict(key=key), json=chat.gemini_json | dict(
                generationConfig=dict(
                    temperature=0.7,
                    max_output_tokens=1024
                )
            ))
            return '\n'.join(part.get('text', '') for part in r.json()['candidates'][0]['content']['parts'])
    except KeyError: raise Exception(f'Cannot get gemini response with key "{key}", {r.status_code} - {r.text}')
    except TypeError: raise Exception(f'Cannot get gemini response with key "{key}", {r.status_code} - {r.text}')


if __name__ == '__main__':
    api_key = random.choice(json.load(open('api_data.json')).get('gemini', []))

    cm = ChatManager()
    cm.addText('user', 'What does this image say?')
    cm.addImages('user', open('image.png', 'rb').read())

    print(asyncio.run(getGeminiResponse(cm, api_key)))


