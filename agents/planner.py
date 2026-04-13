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


def plan_task(command):
    print("DEBUG -> Planner received:", command)
    if _looks_like_general_qa(command):
        print("DEBUG -> Planner output: web_agent (QA heuristic)")
        return "web_agent"

    prompt = f"""
You are a strict routing planner. Reply with exactly one token: the agent name. No punctuation or explanation.

Agents:
- web_agent — Questions, explanations, definitions, general knowledge, chat, "what/why/how" (not about opening apps), summaries, opinions on topics.
- system_agent — ONLY launching a desktop app: user clearly says open/launch/start + short app name (e.g. "open chrome", "launch spotify"). NOT for questions or sentences like "explain X".
- automation_agent — Click, type, scroll, automate the UI, keyboard/mouse control.
- memory_agent — Remember or recall stored facts the user asked to save.
- code_agent — Write, fix, or explain source code and programming.

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
