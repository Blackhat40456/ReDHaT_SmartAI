"""
Long-term memory helpers for the auto-reply bot.

Everything here is deterministic (no extra API calls): facts such as the
user's UID, country and name are extracted from their messages with
patterns, saved per user, and injected into the system prompt on every
turn, so the bot keeps knowing them long after the 40-message history
window has moved on and never has to ask again.
"""

import re

# ---------------------------------------------------------------- countries

_COUNTRY_NAMES = """Afghanistan|Albania|Algeria|Andorra|Angola|Argentina|Armenia|Australia|Austria|Azerbaijan|Bahamas|Bahrain|Bangladesh|Barbados|Belarus|Belgium|Belize|Benin|Bhutan|Bolivia|Bosnia and Herzegovina|Botswana|Brazil|Brunei|Bulgaria|Burkina Faso|Burundi|Cambodia|Cameroon|Canada|Cape Verde|Central African Republic|Chad|Chile|China|Colombia|Comoros|Congo|Costa Rica|Croatia|Cuba|Cyprus|Czech Republic|Denmark|Djibouti|Dominican Republic|Ecuador|Egypt|El Salvador|Equatorial Guinea|Eritrea|Estonia|Eswatini|Ethiopia|Fiji|Finland|France|Gabon|Gambia|Georgia|Germany|Ghana|Greece|Guatemala|Guinea|Guinea-Bissau|Guyana|Haiti|Honduras|Hungary|Iceland|India|Indonesia|Iran|Iraq|Ireland|Israel|Italy|Ivory Coast|Jamaica|Japan|Jordan|Kazakhstan|Kenya|Kuwait|Kyrgyzstan|Laos|Latvia|Lebanon|Lesotho|Liberia|Libya|Lithuania|Luxembourg|Madagascar|Malawi|Malaysia|Maldives|Mali|Malta|Mauritania|Mauritius|Mexico|Moldova|Mongolia|Montenegro|Morocco|Mozambique|Myanmar|Namibia|Nepal|Netherlands|New Zealand|Nicaragua|Niger|Nigeria|North Korea|North Macedonia|Norway|Oman|Pakistan|Palestine|Panama|Papua New Guinea|Paraguay|Peru|Philippines|Poland|Portugal|Qatar|Romania|Russia|Rwanda|Saudi Arabia|Senegal|Serbia|Sierra Leone|Singapore|Slovakia|Slovenia|Somalia|South Africa|South Korea|South Sudan|Spain|Sri Lanka|Sudan|Suriname|Sweden|Switzerland|Syria|Taiwan|Tajikistan|Tanzania|Thailand|Togo|Trinidad and Tobago|Tunisia|Turkey|Turkmenistan|Uganda|Ukraine|United Arab Emirates|United Kingdom|United States|Uruguay|Uzbekistan|Venezuela|Vietnam|Yemen|Zambia|Zimbabwe"""

# Extra spellings / demonyms. Demonyms that are also language names
# (french, spanish, german...) are left out on purpose to avoid wrong matches.
_ALIASES = {
    'bd': 'Bangladesh', 'bangla desh': 'Bangladesh', 'bangladeshi': 'Bangladesh',
    'indian': 'India', 'pakistani': 'Pakistan', 'pak': 'Pakistan',
    'nigerian': 'Nigeria', 'ghanaian': 'Ghana', 'kenyan': 'Kenya',
    'south african': 'South Africa', 'ethiopian': 'Ethiopia', 'egyptian': 'Egypt',
    'moroccan': 'Morocco', 'algerian': 'Algeria', 'tunisian': 'Tunisia',
    'ugandan': 'Uganda', 'tanzanian': 'Tanzania', 'zambian': 'Zambia',
    'zimbabwean': 'Zimbabwe', 'cameroonian': 'Cameroon', 'senegalese': 'Senegal',
    'ivorian': 'Ivory Coast', 'cote d ivoire': 'Ivory Coast',
    'nepali': 'Nepal', 'nepalese': 'Nepal', 'srilanka': 'Sri Lanka', 'sri lankan': 'Sri Lanka',
    'indonesian': 'Indonesia', 'filipino': 'Philippines', 'philippine': 'Philippines',
    'malaysian': 'Malaysia', 'vietnamese': 'Vietnam', 'cambodian': 'Cambodia',
    'burmese': 'Myanmar', 'afghan': 'Afghanistan', 'iranian': 'Iran', 'iraqi': 'Iraq',
    'turkiye': 'Turkey', 'turkish': 'Turkey', 'saudi': 'Saudi Arabia', 'ksa': 'Saudi Arabia',
    'emirati': 'United Arab Emirates', 'uae': 'United Arab Emirates',
    'qatari': 'Qatar', 'kuwaiti': 'Kuwait', 'omani': 'Oman', 'yemeni': 'Yemen',
    'lebanese': 'Lebanon', 'jordanian': 'Jordan', 'syrian': 'Syria',
    'uzbek': 'Uzbekistan', 'kazakh': 'Kazakhstan', 'kyrgyz': 'Kyrgyzstan',
    'tajik': 'Tajikistan', 'turkmen': 'Turkmenistan', 'azerbaijani': 'Azerbaijan',
    'armenian': 'Armenia', 'georgian': 'Georgia', 'russian': 'Russia',
    'ukrainian': 'Ukraine', 'belarusian': 'Belarus', 'polish': 'Poland',
    'romanian': 'Romania', 'bulgarian': 'Bulgaria', 'serbian': 'Serbia',
    'croatian': 'Croatia', 'brazilian': 'Brazil', 'argentinian': 'Argentina',
    'argentine': 'Argentina', 'mexican': 'Mexico', 'colombian': 'Colombia',
    'peruvian': 'Peru', 'chilean': 'Chile', 'venezuelan': 'Venezuela',
    'ecuadorian': 'Ecuador', 'bolivian': 'Bolivia',
    'uk': 'United Kingdom', 'england': 'United Kingdom', 'britain': 'United Kingdom',
    'great britain': 'United Kingdom', 'british': 'United Kingdom',
    'usa': 'United States', 'america': 'United States', 'american': 'United States',
    'united states of america': 'United States',
    'canadian': 'Canada', 'australian': 'Australia', 'holland': 'Netherlands',
    'korea': 'South Korea',
}

_COUNTRY_LOOKUP = {n.lower(): n for n in _COUNTRY_NAMES.split('|')}
_COUNTRY_LOOKUP.update(_ALIASES)


def _norm_phrase(text: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r"[^a-z\s]", ' ', text.lower())).strip()


def resolve_country(phrase: str, min_len: int = 2):
    """Turn a free-text phrase ("bangladesh and i am 20") into a country name."""
    words = _norm_phrase(phrase).split()
    for n in (3, 2, 1):
        if len(words) >= n:
            cand = ' '.join(words[:n])
            if len(cand) >= min_len and cand in _COUNTRY_LOOKUP:
                return _COUNTRY_LOOKUP[cand]
    return None


_COUNTRY_CTX_RE = re.compile(
    r"(?:\b(?:i am|i'm|im|we are|we're)\s+from|\bfrom|\bi live in|\blive in|\bliving in|"
    r"\bi stay in|\bstaying in|\bbased in|\bi am in|\bi'm in|\bim in|"
    r"\bmy country is|\bcountry\s*(?:is|:|-)?|\blocation\s*(?:is|:|-)?)\s+([A-Za-z][A-Za-z .'-]{1,40})",
    re.I,
)


def _extract_country(text: str):
    m = _COUNTRY_CTX_RE.search(text)
    if m:
        c = resolve_country(m.group(1))
        if c:
            return c
    # A bare reply such as "Bangladesh" / "Nigerian" -> only for short messages
    words = _norm_phrase(text).split()
    if 0 < len(words) <= 3:
        c = resolve_country(' '.join(words), min_len=4)
        if c:
            return c
    return None


# -------------------------------------------------------------------- name

_NAME_RE = re.compile(
    r"(?:\bmy name is|\bmy name's|\bname is|\bi am called|\bcall me|\bpeople call me)\s+"
    r"([A-Za-z][A-Za-z'.\-]{1,20}(?:\s+[A-Za-z][A-Za-z'.\-]{1,20}){0,2})",
    re.I,
)
_NAME_STOP = {
    'and', 'from', 'i', 'im', "i'm", 'my', 'but', 'so', 'the', 'a', 'an', 'is', 'are',
    'living', 'live', 'here', 'in', 'of', 'who', 'not', 'because', 'please', 'sir',
    'bro', 'brother', 'uid', 'id', 'country', 'also', 'ok', 'okay',
}


def _extract_name(text: str):
    m = _NAME_RE.search(text)
    if not m:
        return None
    parts = []
    for tok in m.group(1).split():
        if tok.lower() in _NAME_STOP:
            break
        parts.append(tok)
    name = ' '.join(parts).strip(" .'-")
    if 2 <= len(name) <= 40:
        return name.title() if name.islower() else name
    return None


# --------------------------------------------------------------------- uid

_UID_KW_RE = re.compile(
    r"(?:\buid\b|\bu\.i\.d\b|\bplayer id\b|\baccount id\b|\bid number\b|\bid no\b|\bid\b)[^0-9\n]{0,15}(\d{7,12})",
    re.I,
)
_DIGITS_ONLY_RE = re.compile(r"^\D{0,3}(\d{7,12})\D{0,3}$")


def _extract_uid(text: str):
    m = _UID_KW_RE.search(text) or _DIGITS_ONLY_RE.match(text.strip())
    return m.group(1) if m else None


# ------------------------------------------------------------------ public

def extract_facts(text: str) -> dict:
    """Facts the user stated in a single message (empty dict if none)."""
    facts = {}
    if not text:
        return facts
    if uid := _extract_uid(text):
        facts['uid'] = uid
    if name := _extract_name(text):
        facts['name'] = name
    if country := _extract_country(text):
        facts['country'] = country
    return facts


def facts_from_tool_result(content) -> dict:
    """Pick up the outcome of the check_uid_status tool so it is remembered too."""
    if not isinstance(content, str) or not content.startswith('UID ('):
        return {}
    facts = {'uid_status': content.strip()[:240]}
    if m := re.match(r'UID \((\d+)\)', content):
        facts['uid'] = m.group(1)
    return facts


_LABELS = [
    ('account_name', 'Telegram account name'),
    ('name', 'Name the user told you'),
    ('country', 'Country'),
    ('uid', 'Player UID'),
    ('uid_status', 'Latest UID check result'),
]


def build_memory_block(facts: dict) -> str:
    known = dict(_LABELS)
    lines = [f'- {label}: {facts[key]}' for key, label in _LABELS if facts.get(key)]
    lines += [f'- {k}: {v}' for k, v in facts.items() if k not in known and v]
    body = '\n'.join(lines) if lines else '- (nothing known yet)'
    return (
        '[MEMORY: facts you ALREADY know about this user. Use them naturally and '
        'NEVER ask the user for any of these again.]\n' + body
    )


BEHAVIOR_RULES = """=== CONVERSATION RULES (follow strictly) ===
1. You have memory of this user (see the MEMORY block). Never ask again for anything listed there (name, country, UID...). If the UID is already in MEMORY, use it directly; if the user gives a new one, use the new one.
2. This is an ongoing conversation. Do NOT greet again with "Hello / Hi, how can I help you?" and do NOT ask "what is your name?" once you have already talked. Always answer what the user's LAST message actually says, using earlier messages as context.
3. If the user sends an image, sticker, GIF or voice note that you cannot clearly understand, do not invent details and do not change the topic. Say briefly and naturally that you could not make it out and ask them to resend it or describe it in a few words.
4. Stay consistent with what was already said in this chat; never contradict yourself or repeat the same question."""

RETRY_NOTE = (
    "Your previous draft was a generic greeting / name question, which is wrong here because "
    "you are already mid-conversation with this user. Write a NEW reply that directly answers "
    "the user's last message (if it was an image or sticker you can't understand, say so "
    "briefly and ask them to resend or describe it). No greeting, don't ask their name."
)

_GENERIC_RE = re.compile('|'.join([
    r"\bhow (can|may|could|should) i (help|assist)( you)?( today| now)?\b",
    r"\bwhat('s| is| was) your name\b",
    r"\b(may|can) i (know|have|get) your name\b",
    r"\bwhat can i do for you\b",
    r"\bhow can i be of (help|assistance)\b",
]), re.I)
_ONLY_GREETING_RE = re.compile(r"^\W*(hi|hello|hey|hii+|hlo|assalamu alaikum|salam)\W*$", re.I)


def is_generic_reply(reply: str) -> bool:
    reply = (reply or '').strip()
    return bool(reply) and bool(_GENERIC_RE.search(reply) or _ONLY_GREETING_RE.match(reply))


def strip_generic_sentences(reply: str) -> str:
    parts = re.split(r'(?<=[.!?])\s+|\n+', reply or '')
    kept = [p for p in parts if p.strip() and not _GENERIC_RE.search(p) and not _ONLY_GREETING_RE.match(p)]
    return ' '.join(kept).strip()


def fallback_line(kind: str) -> str:
    if kind == 'photo':
        return "I couldn't see that image clearly 😅 Can you send it again or tell me what it's about?"
    if kind == 'voice':
        return "I couldn't catch that voice message properly. Can you send it again or type it out?"
    return "Sorry, I didn't get that properly. Can you say it once more?"
