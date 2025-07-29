from AI.cloudflare import getCloudflareResponse
from AI.gemini import getGeminiResponse
from AI.groq import getGroqResponse
from AI.together import getTogetherResponse
from datetime import datetime, timezone
from AI.chat_manager import ChatManager
import traceback

FUNCTIONS = dict(
    groq=getGroqResponse,
    gemini=getGeminiResponse,
    cloudflare=getCloudflareResponse,
    together=getTogetherResponse
)


cm = ChatManager()
cm.addText('user', 'Say "working"')


async def checkAPI(all_keys: list[tuple[str, str]], cache_obj: dict):
    if cache_obj.get('running'): return
    cache_obj['running'] = True
    cache_obj['data'] = ''
    rs = []
    for provider, key in all_keys:
        try:
            r = await FUNCTIONS[provider](cm, key)
        except:
            cache_obj['data'] += traceback.format_exc() + '\n'
            r = None
        rs.append(f'{provider.title()} - "{key}" - {r}')
        cache_obj['data'] += rs[-1] + '\n'

    cache_obj['data'] += '\n\n\n\nResult:\n' + '\n'.join(k for k in rs)
    cache_obj['running'] = False
    cache_obj['last_checked'] = datetime.now(timezone.utc)


