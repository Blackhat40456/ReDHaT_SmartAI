from indicnlp.tokenize.sentence_tokenize import sentence_split as indicnlp
from langdetect import detect
from indicnlp import common
import re, random

common.set_resources_path('./indic_nlp_resources')

def extract_and_replace_urls(text):
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    replacements = {}

    for i, url in enumerate(urls):
        key = f"<<U{i}>>"
        replacements[key] = url
        text = text.replace(url, key)

    return text, replacements

def restore_urls(text, replacements):
    for key, url in replacements.items():
        text = text.replace(key, url)
    return text

def split(text: str, max_words: int = None):
    max_words = max_words or random.randint(20, 35)
    text, replacements = extract_and_replace_urls(text)
    lang = detect(text)
    sents = indicnlp(text, lang)
    sents = [restore_urls(i, replacements) for i in sents]
    parts = []
    current_part = []
    current_count = 0

    for sent in sents:
        sent_words = sent.split()
        if current_count + len(sent_words) > max_words and current_part:
            parts.append(' '.join(current_part))
            current_part = []
            current_count = 0
        current_part.append(sent)
        current_count += len(sent_words)

    if current_part:
        parts.append(' '.join(current_part))

    return parts


if __name__ == '__main__':
    en = 'A cow is a domestic animal that can be seen in our homes. https://cutt.ly/rjeur @Rehdat It is a four-legged animal that comes in various colours like white, black or brown. It may also have large spots on its body. A cow has two small eyes and ears, a big nose, two sharp horns and a long tail with hair at the end.'
    bn = 'গরু হল একটি গৃহপালিত প্রাণী যা আমাদের বাড়িতে দেখা যায়। https://cutt.ly/rjeur @Rehdat এটি একটি চার পায়ের প্রাণী যা সাদা, কালো বা বাদামী রঙের বিভিন্ন রঙে পাওয়া যায়। এর শরীরে বড় বড় দাগও থাকতে পারে। একটি গরুর দুটি ছোট চোখ এবং কান, একটি বড় নাক, দুটি ধারালো শিং এবং শেষ প্রান্তে লোম সহ একটি লম্বা লেজ থাকে।'
    hi = 'गाय एक पालतू पशु है जिसे हम अपने घरों में आसानी से देख सकते हैं। https://cutt.ly/rjeur @Rehdat यह एक चार पैरों वाला जानवर है जो सफेद, काले या भूरे जैसे विभिन्न रंगों में पाया जाता है। इसके शरीर पर बड़े-बड़े धब्बे भी हो सकते हैं। गाय की दो छोटी आँखें और कान, एक बड़ी नाक, दो नुकीले सींग और अंत में बालों वाली एक लंबी पूंछ होती है।'

    print(split(en))


