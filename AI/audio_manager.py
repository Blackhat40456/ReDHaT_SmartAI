from .cloudflare import getCloudflareStoT
from .gemini import getGeminiStoT
from .groq import getGroqStoT
from .together import getTogetherStoT
from random import choice
import hashlib, traceback

TFUNCTIONS = dict(
    groq=getGroqStoT,
    gemini=getGeminiStoT,
    cloudflare=getCloudflareStoT,
    together=getTogetherStoT
)
CACHE = dict()


def add_cache(k, v):
    CACHE[k] = v
    if len(CACHE) > 500:
        oldest_key = next(iter(CACHE))
        del CACHE[oldest_key]


async def speechToText(audio: bytes, all_keys: list[tuple[str, str]]):
    hs = hashlib.sha256(audio).hexdigest()
    if hs in CACHE: return CACHE[hs]
    keys = all_keys.copy()
    while keys:
        provider, api_key = keys.pop(keys.index(choice(keys)))
        # print('Trying on', provider)
        try:
            stext = await TFUNCTIONS[provider](audio, api_key)
            add_cache(hs, stext)
            return stext
        except KeyError:
            print(f'Speech to Text: Provider {provider} is unknown')
        except Exception as err:
            err = str(err)
            # Remember to update this same part in __init__.py
            # exc = traceback.format_exc()
            if '", 429 -' not in err and 'supports up to 5 images' not in err:
                print(err)


