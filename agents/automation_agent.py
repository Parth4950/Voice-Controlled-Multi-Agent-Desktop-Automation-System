from agents.execution import execute
from tools.log import safe_log


def run_automation_agent(command):
    lower = command.lower()

    # YouTube play path
    if any(kw in lower for kw in ("play", "youtube")):
        query = lower
        for word in ["play", "search", "automate"]:
            query = query.replace(word, "")
        query = " ".join(query.split())

        result = execute("play_media_advanced", {"query": query})
        if result == "success":
            return "Done, playing now"
        if result == "fallback":
            return "Couldn't automate that perfectly, but I opened the search for you"
        return "Bruh, automation failed this round"

    # Navigate
    for prefix in ("go to ", "navigate to ", "open "):
        if lower.startswith(prefix):
            url = lower[len(prefix):].strip()
            if url:
                result = execute("navigate", {"url": url})
                return result or "Tried to navigate"

    # Click
    if lower.startswith("click "):
        target = lower.replace("click on ", "").replace("click ", "", 1).strip()
        if target:
            result = execute("web_click", {"target": target})
            return result or "Tried to click"

    # Type
    if lower.startswith("type "):
        text = lower[5:].strip()
        if text:
            result = execute("web_type", {"text": text})
            return result or "Tried to type"

    # Scroll
    if "scroll" in lower:
        direction = "up" if "up" in lower else "down"
        result = execute("web_scroll", {"direction": direction})
        return result or "Tried to scroll"

    safe_log("DEBUG -> automation_agent: unrecognized command:", command)
    return "Not sure what to automate there"
