import re

from agents.execution import execute
from agents.web_agent import run_web_agent


def _clean_app_name(text):
    cleaned = text.strip().lower()
    cleaned = re.sub(r"\b(please|for me|thanks?)\b", "", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def run_system_agent(command):
    """
    Only open/launch/start a desktop app when the user clearly asks for it.
    Otherwise delegate to web_agent (planner can mislabel Q&A as system).
    """
    c = command.strip().lower()
    m = re.match(r"^(?:please\s+)?(open|launch|start)\s+(.+)$", c)
    if not m:
        print("DEBUG -> system_agent: not an open/launch/start command, using web_agent")
        return run_web_agent(command)

    rest = _clean_app_name(m.group(2))
    if not rest:
        return "Tell me which app to open."

    words = rest.split()
    if len(words) > 12 or len(rest) > 80:
        print("DEBUG -> system_agent: tail too long for an app name, using web_agent")
        return run_web_agent(command)

    app_name = rest
    opened = execute("open_app", {"app": app_name})
    if opened:
        return f"Opening {app_name}"
    return f"I couldn't open {app_name}. Try saying just 'open {app_name}'."
