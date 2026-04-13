import re


def _extract_after(command, keyword):
    """Return everything after the first occurrence of keyword."""
    idx = command.index(keyword)
    return command[idx + len(keyword):].strip()


def route_command(command: str):
    command = command.strip().lower()

    automation_keywords = [
        "now", "play it", "start", "click", "first", "auto", "automatically",
    ]
    _screen_keywords = [
        "looking at", "on my screen", "on screen", "what do you see",
        "what's on my screen", "this code", "the code", "my screen",
        "what am i looking", "what code", "read my screen",
        "see my screen", "what is on screen", "what app is open",
        "what is this code", "what is this app",
        "currently on my", "what is on my", "what's on my",
    ]
    _code_keywords = [
        "debug", "fix this", "fix the", "this error", "this issue", "this problem",
        "this bug",
    ]

    # --- Memory ---
    if "remember" in command:
        cleaned = command.replace("remember", "", 1).strip()
        if cleaned.startswith("my ") and " is " in cleaned:
            key_part, value = cleaned.split(" is ", 1)
            key = key_part.replace("my ", "", 1).strip()
            value = value.strip()
            if key and value:
                return ("remember", {"key": key, "value": value})
        return ("unknown", {})

    if "what is my" in command:
        key = command.replace("what is my", "", 1).strip()
        if key:
            return ("recall", {"key": key})
        return ("unknown", {})

    # --- Screen analysis (only clearly screen-related commands) ---
    if any(keyword in command for keyword in _screen_keywords):
        return ("analyze_context", {"query": command})

    # --- Code-specific keywords that need screen context ---
    if any(keyword in command for keyword in _code_keywords):
        return ("analyze_context", {"query": command})

    # --- Bare single-word commands ---
    if command == "stop":
        return ("close_app", {"app": "last"})
    if command == "screenshot":
        return ("screenshot", {})
    if command == "mute":
        return ("volume", {"action": "mute"})

    # --- Screenshot ---
    if re.search(r"\bscreenshot\b", command):
        return ("screenshot", {})

    # --- Volume ---
    vol_match = re.search(r"\bvolume\s+(up|down|mute)\b", command)
    if vol_match:
        return ("volume", {"action": vol_match.group(1)})
    if re.search(r"\bmute\b", command):
        return ("volume", {"action": "mute"})

    # --- Close / Kill / Quit app ---
    close_match = re.match(r"^(?:close|kill|quit|stop|exit)\s+(.+)$", command)
    if close_match:
        app_name = close_match.group(1).strip()
        if app_name:
            return ("close_app", {"app": app_name})

    # --- Open app (+ aliases: launch, start, run) ---
    open_match = re.match(r"^(?:open|launch|start|run)\s+(.+)$", command)
    if open_match:
        app_name = open_match.group(1).strip()
        if app_name:
            print("DEBUG -> Extracted app:", app_name)
            return ("open_app", {"app": app_name})
        return ("unknown", {})

    # --- Search (+ aliases: google, look up, find, find me) ---
    search_match = re.match(r"^(?:search|google|look\s*up|find(?:\s+me)?)\s+(.+)$", command)
    if search_match:
        query = search_match.group(1).strip()
        if query:
            return ("search", {"query": query})

    # --- Navigate / Go to ---
    nav_match = re.match(r"^(?:go\s+to|navigate\s+to|navigate)\s+(.+)$", command)
    if nav_match:
        url = nav_match.group(1).strip()
        if url:
            return ("navigate", {"url": url})

    # --- Web click ---
    click_match = re.match(r"^click\s+(?:on\s+)?(.+)$", command)
    if click_match:
        target = click_match.group(1).strip()
        if target:
            return ("web_click", {"target": target})

    # --- Web type ---
    type_match = re.match(r"^type\s+(.+)$", command)
    if type_match:
        text = type_match.group(1).strip()
        if text:
            return ("web_type", {"text": text})

    # --- Web scroll ---
    scroll_match = re.search(r"\bscroll\s+(up|down)\b", command)
    if scroll_match:
        return ("web_scroll", {"direction": scroll_match.group(1)})

    # --- Play ---
    if "play" in command:
        cleaned_query = command.replace("play", "", 1).strip()
        cleaned_query = cleaned_query.replace("on youtube", "").strip()
        if cleaned_query in ("first video", "the first video"):
            return ("unknown", {})
        if any(keyword in command for keyword in automation_keywords):
            return ("play_media_advanced", {"query": cleaned_query})
        return ("play_media", {"query": cleaned_query})

    return ("unknown", {})
