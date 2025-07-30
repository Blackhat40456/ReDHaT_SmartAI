from .chat_manager import ChatManager
from .cloudflare import getCloudflareResponse
from .gemini import getGeminiResponse
from .groq import getGroqResponse
from .together import getTogetherResponse
from random import choice
from .tools import tools
import traceback, json, re, random


FUNCTIONS = dict(
    groq=getGroqResponse,
    gemini=getGeminiResponse,
    cloudflare=getCloudflareResponse,
    together=getTogetherResponse
)


tool_funcs = {}
for t in tools:
    tool_funcs[t['function']['name'].__name__] = t['function']['name']
    t['function']['name'] = t['function']['name'].__name__


async def check_if_tool_and_run(chat: ChatManager, all_keys: list[tuple[str, str]], resp, bot):
    if isinstance(resp, str):
        if 'check_uid_status' in resp:
            nums = re.findall(r'\d{7,12}', resp)
            uid = int(nums[0]) if nums else None
            if uid:
                return await check_if_tool_and_run(chat, all_keys, [dict(function=dict(name='check_uid_status', arguments=json.dumps(dict(uid=uid))), type='function', id=f'fn___ds{random.randint(1000, 9999)}')], bot)
            else:
                print('Invalid UID in text plain', resp)
        else:
            return resp
    if isinstance(resp, list):
        resp = resp.copy()
        for k in resp:
            k['id'] = f'fncll{random.randint(1000, 9999)}'
        
        chat.addToolCalls(resp)
        for c in resp:
            tr = await tool_funcs[c['function']['name']](bot, **json.loads(c['function']['arguments']))
            print(tr)
            chat.addToolResponse(c['id'], tr, c['function']['name'])
        return await getAIResponse(chat, all_keys, bot, ['together'])


async def getAIResponse(chat: ChatManager, all_keys: list[tuple[str, str]], bot = None, excludes: list = []):
    keys = all_keys.copy()
    while keys:
        provider, api_key = keys.pop(keys.index(choice(keys)))
        if provider in excludes: continue
        # print('Trying on', provider)
        try:
            resp = await FUNCTIONS[provider](chat, api_key, tools)
            return await check_if_tool_and_run(chat, all_keys, resp, bot)
        except KeyError:
            # print(f'Provider {provider} is unknown')
            pass
        except Exception as err:
            err = str(err)
            if 'AiError: Bad input' in err:
                json.dump(chat.data, open('test.json', 'w'), indent=4)
            # Remember to update this same part in audio_manager.py
            # err = traceback.format_exc()
            if '", 429 -' not in err and 'supports up to 5 images' not in err:
                print(err)
    




