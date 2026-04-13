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
                remember(key, value)
                return f"Got it, I’ll remember your {key}"

    if "what is my" in command:
        key = command.replace("what is my", "", 1).strip()
        if key:
            value = recall(key)
            if value:
                return f"Your {key} is {value}"
            return "I don’t know that yet"

    return "I don’t know that yet"
