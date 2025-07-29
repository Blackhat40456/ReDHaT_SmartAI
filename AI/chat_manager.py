import typing, filetype, base64, inspect, re, json
from httpx import Client, AsyncClient
from .token_manager import truncate_messages, count_tokens


def bytes_to_data_url(data_bytes: bytes) -> str:
    kind = filetype.guess(data_bytes)
    if kind is None:
        raise ValueError("Unsupported type.")

    base64_str = base64.b64encode(data_bytes).decode('utf-8')
    data_url = f"data:{kind.mime};base64,{base64_str}"
    return data_url


class UrlLike(str): pass

class ChatManager:
    def __init__(self, system_prompt: str = None, all_keys: list[tuple[str, str]] = None):
        self.messages = []
        self.__funcNames = dict()
        self.has_image = False
        self.all_keys = all_keys
        if all_keys:
            from .audio_manager import speechToText
            self.speechToText = speechToText
        if system_prompt:
            self.addText('system', system_prompt)
    
    def addToolCalls(self, data: list):
        self.messages.append(dict(role='assistant', tool_calls=data))
        return self

    def addToolResponse(self, call_id: str, content, func_name: str = None):
        self.__funcNames[call_id] = func_name
        self.messages.append(dict(role='tool', tool_call_id=call_id, content=content))
        return self

    def addText(self, role: typing.Literal['system', 'user', 'assistant'], text: str):
        self.messages.append(dict(role=role, content=text))
        self.has_image = True
        return self

    def addImages(self, role: typing.Literal['system', 'user', 'assistant'], images: typing.Union[UrlLike, bytes, list[typing.Union[UrlLike, bytes]]]):
        if self._is_async_context():
            return self._async_add_image(role, images)
        else:
            return self._sync_add_image(role, images)

    async def addAudio(self, role: typing.Literal['system', 'user', 'assistant'], audio: bytes):
        if not self.all_keys:
            raise Exception('API Keys are required to add audio files')
        stext = await self.speechToText(audio, self.all_keys)
        if st := (stext or "").strip():
            self.addText(role, st)
        else:
            print('Cannot add audio file, AI cannot transcribe it')
        return stext
    
    def truncated_data(self, max_tokens: int = 121_000):
        return self.truncated_json(max_tokens)
    
    def truncated_json(self, max_tokens: int = 121_000, isCF=False):
        return truncate_messages(self.messages, int(max_tokens))

    @property
    def token_count(self):
        return sum(count_tokens(m) for m in self.messages)

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
            # dict(role='tool', tool_call_id=call_id, content=content)
            if m['role'] == 'system': continue
            all_parts = []
            a_part = dict()
            if m['role'] == 'tool':
                tci = m['tool_call_id']
                fname = self.__funcNames[tci]
                rs = m['content']
                try: rs = json.loads(rs)
                except: pass
                a_part['function_response'] = dict(name=fname, response=dict(result=rs))
            elif tc := m.get('tool_calls'):
                for itc in tc:
                    parsedArgs = itc['function']['arguments']
                    try: parsedArgs = json.loads(parsedArgs)
                    except: pass
                    all_parts.append(dict(function_call=dict(name=itc['function']['name'], args=parsedArgs)))
            elif isinstance(m['content'], str):
                a_part['text'] = m['content']
            elif isinstance(m['content'], list):
                b64_url = m['content'][0]['image_url']['url']
                match = re.match(r"data:(.*?);base64,(.*)", b64_url)
                a_part['inline_data'] = dict(
                    mime_type=match.group(1),
                    data=match.group(2)
                )
            if a_part: all_parts.append(a_part)
            if all_parts:
                gemRole = 'user'
                if m['role'] == 'assistant': gemRole = 'model'
                elif m['role'] == 'tool': gemRole = 'function'
                gemData['contents'].append(dict(parts=all_parts, role=gemRole))
        return gemData

    def _sync_add_image(self, role, images):
        if not isinstance(images, list):
            images = [images]
        modImages = []
        for i in images:
            if isinstance(i, str) and not i.startswith('data'):
                with Client(follow_redirects=True, verify=False) as s:
                    modImages.append(bytes_to_data_url(s.get(i).content))
            elif isinstance(i, bytes):
                modImages.append(bytes_to_data_url(i))
            else:
                print('Unknown data provided in addImages, skipping')
        
        for k in modImages:
            self.messages.append(dict(role=role, content=[dict(type='image_url', image_url=dict(url=k))]))
        return self

    async def _async_add_image(self, role, images):
        if not isinstance(images, list):
            images = [images]
        modImages = []
        for i in images:
            if isinstance(i, str) and not i.startswith('data'):
                async with AsyncClient(follow_redirects=True, verify=False) as s:
                    modImages.append(bytes_to_data_url((await s.get(i)).content))
            elif isinstance(i, bytes):
                modImages.append(bytes_to_data_url(i))
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


