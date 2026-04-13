from typing import Optional

from ai.gemini import ask_gemini

_VALID_AGENTS = frozenset(
    {
        "code_agent",
        "web_agent",
        "system_agent",
        "automation_agent",
        "memory_agent",
    }
)


def _normalize_agent_name(raw: str) -> Optional[str]:
    if not raw:
        return None
    text = raw.strip().lower()
    if not text:
        return None
    first = text.split()[0]
    if first in _VALID_AGENTS:
        return first
    for name in _VALID_AGENTS:
        if name in text:
            return name
    return None


def _looks_like_general_qa(command: str) -> bool:
    """Obvious questions/explanations — route to web_agent without relying on Gemini."""
    c = command.strip().lower()
    prefixes = (
        "explain ",
        "what is ",
        "what are ",
        "who is ",
        "who are ",
        "tell me ",
        "how does ",
        "how do ",
        "how can ",
        "why ",
        "define ",
        "describe ",
        "what was ",
        "what does ",
        "can you explain",
    )
    return any(c.startswith(p) for p in prefixes)


def _looks_like_screen_question(command: str) -> bool:
    """Route screen/visual questions to code_agent without a Gemini call."""
    c = command.strip().lower()
    screen_hints = (
        "looking at", "on my screen", "on screen", "my screen",
        "what do you see", "what am i", "this code", "the code",
        "read my screen", "what code", "screen text",
        "currently on my", "what is on my", "what's on my",
    )
    return any(h in c for h in screen_hints)


def _looks_like_conversation(command: str) -> bool:
    """Detect casual chat that should go straight to web_agent, no Gemini routing needed."""
    c = command.strip().lower()
    chat_starts = (
        "hi", "hello", "hey", "how are you", "what's up", "sup",
        "do you", "can you", "are you", "would you",
        "tell me", "talk to me", "i think", "i feel", "i want",
        "thanks", "thank you", "good morning", "good night",
        "yo", "wassup", "achcha", "haan", "nahi",
    )
    if any(c.startswith(p) for p in chat_starts):
        return True
    if len(c.split()) <= 5 and "?" in c:
        return True
    return False


def _looks_like_memory(command: str) -> bool:
    """Detect remember/recall patterns that belong to memory_agent."""
    import re
    c = command.strip().lower()
    if "remember" in c:
        return True
    if "what is my" in c:
        return True
    if re.match(r"^my\s+\w+\s+is\s+", c):
        return True
    if re.match(r"^(?:call me|my name is|i am|i'm|im)\s+", c):
        return True
    return False


def _looks_like_short_chat(command: str) -> bool:
    """Short phrases with no technical keywords — just casual chat for web_agent."""
    c = command.strip().lower()
    words = c.split()
    if len(words) > 8:
        return False
    skip = (
        "open", "launch", "start", "close", "kill", "play", "search",
        "click", "type", "scroll", "screenshot", "volume", "mute",
        "remember", "screen", "code", "debug", "fix",
    )
    if any(k in c for k in skip):
        return False
    if len(words) <= 6:
        return True
    return False


def plan_task(command):
    print("DEBUG -> Planner received:", command)

    if _looks_like_screen_question(command):
        print("DEBUG -> Planner output: code_agent (screen heuristic)")
        return "code_agent"

    if _looks_like_memory(command):
        print("DEBUG -> Planner output: memory_agent (memory heuristic)")
        return "memory_agent"

    if _looks_like_conversation(command):
        print("DEBUG -> Planner output: web_agent (conversation heuristic)")
        return "web_agent"

    if _looks_like_general_qa(command):
        print("DEBUG -> Planner output: web_agent (QA heuristic)")
        return "web_agent"

    if _looks_like_short_chat(command):
        print("DEBUG -> Planner output: web_agent (short chat heuristic)")
        return "web_agent"

    prompt = f"""
You are a strict routing planner. Reply with exactly one token: the agent name. No punctuation or explanation.

Agents:
- web_agent — Questions, explanations, definitions, general knowledge, chat, "what/why/how" (not about opening apps), summaries, opinions on topics.
- system_agent — ONLY launching a desktop app: user clearly says open/launch/start + short app name (e.g. "open chrome", "launch spotify"). NOT for questions or sentences like "explain X".
- automation_agent — Click, type, scroll, automate the UI, keyboard/mouse control.
- memory_agent — Remember or recall stored facts the user asked to save.
- code_agent — Write, fix, or explain source code and programming. Also handles "what am I looking at", "what's on my screen", or any request about what's visible on screen (captures and reads the screen via OCR).

If unsure between web_agent and system_agent, choose web_agent.

Command:
{command}
"""
    try:
        agent_name = ask_gemini(prompt)
    except Exception as e:
        print("ERROR in planner:", str(e))
        agent = "web_agent"
        print("DEBUG -> Planner output:", agent)
        return agent

    agent = _normalize_agent_name(agent_name) if agent_name else None
    if not agent:
        agent = "web_agent"

    print("DEBUG -> Planner output:", agent)
    return agent
