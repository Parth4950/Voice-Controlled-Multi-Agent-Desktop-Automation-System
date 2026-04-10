def route_command(command: str):
    command = command.strip().lower()
    automation_keywords = [
        "now",
        "play it",
        "start",
        "click",
        "first",
        "auto",
        "automatically",
    ]

    if "remember" in command:
        cleaned = command.replace("remember", "", 1).strip()
        if cleaned.startswith("my ") and " is " in cleaned:
            key_part, value = cleaned.split(" is ", 1)
            key = key_part.replace("my ", "", 1).strip()
            value = value.strip()
            if key and value:
                return ("remember", {"key": key, "value": value})
        return ("unknown", {})
    elif "what is my" in command:
        key = command.replace("what is my", "", 1).strip()
        if key:
            return ("recall", {"key": key})
        return ("unknown", {})
    elif "open" in command:
        words = command.split()
        open_index = words.index("open")
        if open_index + 1 < len(words):
            extracted_app_name = " ".join(words[open_index + 1:])
            print("DEBUG -> Extracted app:", extracted_app_name)
            return ("open_app", {"app": extracted_app_name})
        return ("unknown", {})
    elif "search" in command:
        cleaned_query = command.replace("search", "", 1).strip()
        return ("search", {"query": cleaned_query})
    elif "play" in command:
        cleaned_query = command.replace("play", "", 1).strip()
        cleaned_query = cleaned_query.replace("on youtube", "").strip()
        if cleaned_query in ("first video", "the first video"):
            return ("unknown", {})
        if any(keyword in command for keyword in automation_keywords):
            return ("play_media_advanced", {"query": cleaned_query})
        return ("play_media", {"query": cleaned_query})

    return ("unknown", {})
