import tiktoken
import json

ENCODING = tiktoken.encoding_for_model("gpt-4")

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
            content_str = json.dumps(content)
            total_tokens += len(encoding.encode(content_str))

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
        else:
            break

    return system_messages + list(reversed(truncated))



