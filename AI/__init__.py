from .chat_manager import ChatManager
from .cloudflare import getCloudflareResponse
from .gemini import getGeminiResponse
from .groq import getGroqResponse
from .together import getTogetherResponse
from random import choice
import traceback


FUNCTIONS = dict(
    groq=getGroqResponse,
    gemini=getGeminiResponse,
    cloudflare=getCloudflareResponse,
    together=getTogetherResponse
)


async def getAIResponse(chat: ChatManager, all_keys: list[tuple[str, str]]):
    keys = all_keys.copy()
    while keys:
        provider, api_key = keys.pop(keys.index(choice(keys)))
        # print('Trying on', provider)
        try:
            return await FUNCTIONS[provider](chat, api_key)
        except:
            traceback.print_exc()
    




