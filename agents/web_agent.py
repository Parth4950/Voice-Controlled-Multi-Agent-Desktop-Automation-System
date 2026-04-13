from ai.gemini import ask_gemini
from memory.context import update_context, get_context
from agents.personality import bruh_prompt
from tools.system_tools import search_google
from tools.log import safe_log

_REALTIME_HINTS = [
    "weather", "temperature", "forecast",
    "score", "scores",
    "price", "stock", "stocks",
    "time in", "time right now",
    "news today", "latest news",
    "traffic",
]


def _needs_realtime(command):
    lower = command.lower()
    return any(hint in lower for hint in _REALTIME_HINTS)


_REFERENTIAL_WORDS = ("it", "that", "this", "more", "detail", "about it", "about that")


def _is_followup(command: str) -> bool:
    c = command.strip().lower()
    return any(w in c for w in _REFERENTIAL_WORDS)


def run_web_agent(command):
    ctx = get_context()

    searched = False
    if _needs_realtime(command):
        safe_log("DEBUG -> web_agent: real-time question, auto-searching Google")
        search_google(command)
        searched = True

    role = (
        "You answer questions, explain topics, and chat casually.\n"
        "For factual questions, give your best answer. Don't say you can't help.\n"
        "For complaints or insults, roast the user back. NEVER apologize or say sorry."
    )
    if searched:
        role += (
            "\nNote: I've already opened a Google search for this question in the user's browser. "
            "Give a brief helpful answer AND mention that you've also searched Google for them."
        )

    if _is_followup(command):
        last_cmd = ctx.get("last_command") or ""
        last_resp = ctx.get("last_response") or ""
        if last_cmd or last_resp:
            role += (
                f"\nThe user is following up on the previous topic."
                f"\nPrevious question: {last_cmd}"
                f"\nYour previous answer: {last_resp[:300]}"
                f"\nUse this context to understand what they're referring to."
            )

    prompt = bruh_prompt(
        role_context=role,
        user_context=ctx,
        user_query=command,
    )

    response = ask_gemini(prompt)
    update_context(command=command, response=response)
    return response
