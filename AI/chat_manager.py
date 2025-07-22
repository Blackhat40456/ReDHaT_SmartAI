import typing, filetype, base64, inspect, re
from httpx import Client, AsyncClient


def image_bytes_to_data_url(image_bytes: bytes) -> str:
    kind = filetype.guess(image_bytes)
    if kind is None or not kind.mime.startswith("image/"):
        raise ValueError("Unsupported or unknown image type.")

    base64_str = base64.b64encode(image_bytes).decode('utf-8')
    data_url = f"data:{kind.mime};base64,{base64_str}"
    return data_url


class UrlLike(str): pass

class ChatManager:
    messages = []

    def __init__(self, system_prompt: str = None):
        if system_prompt:
            self.addText('system', system_prompt)

    def addText(self, role: typing.Literal['system', 'user', 'assistant'], text: str):
        self.messages.append(dict(role=role, content=text))
        return self
    
    def addImages(self, role: typing.Literal['system', 'user', 'assistant'], images: typing.Union[UrlLike, bytes, list[typing.Union[UrlLike, bytes]]]):
        if self._is_async_context():
            return self._async_add_image(role, images)
        else:
            return self._sync_add_image(role, images)
    
    @property
    def data(self):
        return self.messages
    
    @property
    def json(self):
        return self.data
    
    @property
    def gemini_data(self):
        return self.gemini_json
    
    @property
    def gemini_json(self):
        gemData = dict(contents=[])
        sysPrompts = '\n'.join(map(lambda j: j['content'], filter(lambda x: x['role'] == 'system', self.messages)))
        if sysPrompts:
            gemData['system_instruction'] = dict(parts=[dict(text=sysPrompts)])
        for m in self.messages:
            if m['role'] == 'system': continue
            a_part = dict()
            if type(m['content']) == type('string-text'):
                a_part['text'] = m['content']
            elif type(m['content']) == type(['list-of-img']):
                b64_url = m['content'][0]['image_url']['url']
                match = re.match(r"data:(.*?);base64,(.*)", b64_url)
                a_part['inline_data'] = dict(
                    mime_type=match.group(1),
                    data=match.group(2)
                )
            gemData['contents'].append(dict(parts=[a_part], role='user' if m['role'] == 'user' else 'model'))
        return gemData

    def _sync_add_image(self, role, images):
        if type(images) != type(['any-list']):
            images = [images]
        modImages = []
        for i in images:
            if type(i) == type('url-string') and not i.startswith('data'):
                with Client(follow_redirects=True, verify=False) as s:
                    modImages.append(image_bytes_to_data_url(s.get(i).content))
            elif type(i) == type(b'byte-data'):
                modImages.append(image_bytes_to_data_url(i))
            else:
                print('Unknown data provided in addImages, skipping')
        
        for k in modImages:
            self.messages.append(dict(role=role, content=[dict(type='image_url', image_url=dict(url=k))]))
        return self

    async def _async_add_image(self, role, images):
        if type(images) != type(['any-list']):
            images = [images]
        modImages = []
        for i in images:
            if type(i) == type('url-string') and not i.startswith('data'):
                async with AsyncClient(follow_redirects=True, verify=False) as s:
                    modImages.append(image_bytes_to_data_url((await s.get(i)).content))
            elif type(i) == type(b'byte-data'):
                modImages.append(image_bytes_to_data_url(i))
            else:
                print('Unknown data provided in addImages, skipping')
        
        for k in modImages:
            self.messages.append(dict(role=role, content=[dict(type='image_url', image_url=dict(url=k))]))
        return self
    
    def _is_async_context(self):
        frame = inspect.currentframe()
        while frame:
            if inspect.iscoroutinefunction(frame.f_globals.get(frame.f_code.co_name)):
                return True
            frame = frame.f_back
        return False


