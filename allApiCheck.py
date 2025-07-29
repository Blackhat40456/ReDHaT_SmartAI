from AI.cloudflare import getCloudflareResponse
from AI.gemini import getGeminiResponse
from AI.groq import getGroqResponse
from AI.together import getTogetherResponse
from AI.chat_manager import ChatManager
from AI.token_manager import count_tokens
import json, asyncio, traceback


data = json.load(open('data.json'))
Settings = lambda: data['s']
ApiKeys = lambda: data['a']
IgnoreList = lambda: data['i']


cm = ChatManager()
cm.addText('user', 'Say "working"')


async def main():
    total_res = []
    for provider, key in ApiKeys():
        try:
            r = await globals()[f'get{provider.title()}Response'](cm, key)
        except:
            traceback.print_exc()
            r = None
        total_res.append(f'{provider.title()} - "{key}" - {r}')
        print(total_res[-1])
    
    print('\n\n Result:')
    for k in total_res: print(k)



asyncio.run(main())




