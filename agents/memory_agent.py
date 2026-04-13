import re
from memory.memory import remember, recall


def run_memory_agent(command):
    command = command.strip().lower()

    if "remember" in command:
        cleaned = command.replace("remember", "", 1).strip()
        if cleaned.startswith("my ") and " is " in cleaned:
            key_part, value = cleaned.split(" is ", 1)
            key = key_part.replace("my ", "", 1).strip()
            value = value.strip()
            if key and value:
                previous = remember(key, value)
                if previous and previous != value:
                    return f"Updated. Was {previous}, now {value}."
                return f"Got it, your {key} is {value}."

    if "what is my" in command:
        key = command.replace("what is my", "", 1).strip()
        if key:
            value = recall(key)
            if value:
                return f"Your {key} is {value}"
            return "I don't know that yet."

    m = re.match(r"^my\s+(\w+)\s+is\s+(.+)$", command)
    if m:
        key = m.group(1).strip()
        value = m.group(2).strip()
        if key and value:
            previous = remember(key, value)
            if previous and previous != value:
                return f"Updated. Was {previous}, now {value}."
            return f"Got it, your {key} is {value}."

    m = re.match(r"^(?:i am|i'm|im)\s+(.+)$", command)
    if m:
        value = m.group(1).strip()
        if value:
            remember("identity", value)
            return f"Noted, you're {value}."

    m = re.match(r"^(?:call me|my name is)\s+(.+)$", command)
    if m:
        value = m.group(1).strip()
        if value:
            remember("name", value)
            return f"Got it, {value}."

    return "Not sure what to do with that."
