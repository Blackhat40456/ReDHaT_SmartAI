import tiktoken
import json

ENCODING = tiktoken.encoding_for_model("gpt-4")

# A base64 image is huge as text, but models charge only a small fixed amount for it.
# Counting the raw base64 made every image look enormous, which made truncate_messages
# throw away the image AND the whole earlier conversation.
IMAGE_TOKEN_COST = 1200


def _is_image_message(message) -> bool:
    content = message.get("content") if isinstance(message, dict) else None
    return isinstance(content, list) and any(
        isinstance(p, dict) and (p.get("type") == "image_url" or "image_url" in p) for p in content
    )


def _content_list_tokens(content, encoding) -> int:
    total = 0
    for part in content:
        if isinstance(part, dict):
            if part.get("type") == "image_url" or "image_url" in part:
                total += IMAGE_TOKEN_COST
            elif "text" in part:
                total += len(encoding.encode(str(part["text"])))
            else:
                total += len(encoding.encode(json.dumps(part)))
        else:
            total += len(encoding.encode(str(part)))
    return total

def count_tokens(message, encoding=ENCODING):
    if isinstance(message, str):
        message = dict(content=message)
    total_tokens = 0
    total_tokens += len(encoding.encode(message.get("role", "")))
    total_tokens += len(encoding.encode(message.get("name", "")))

    if "content" in message:
        content = message["content"]
        if isinstance(content, str):
            total_tokens += len(encoding.encode(content))
        elif isinstance(content, list):
            total_tokens += _content_list_tokens(content, encoding)

    if "tool_calls" in message:
        tool_calls_str = json.dumps(message["tool_calls"])
        total_tokens += len(encoding.encode(tool_calls_str))

    if "function_call" in message:
        function_call_str = json.dumps(message["function_call"])
        total_tokens += len(encoding.encode(function_call_str))

    return total_tokens


def truncate_messages(messages: list, max_tokens: int):
    system_messages = [msg for msg in messages if msg.get("role") == "system"]
    other_messages = [msg for msg in messages if msg.get("role") != "system"]

    total_tokens = sum(count_tokens(msg) for msg in system_messages)
    truncated = []

    for message in reversed(other_messages):
        token_count = count_tokens(message)
        if total_tokens + token_count <= max_tokens:
            truncated.append(message)
            total_tokens += token_count
        elif _is_image_message(message):
            continue  # an old image that doesn't fit: skip only it, keep the text history
        else:
            break

    return system_messages + list(reversed(truncated))



