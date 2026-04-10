from tools.system_tools import (
    open_app,
    open_website,
    play_youtube,
    play_youtube_automated as play_youtube_advanced,
    search_google,
)
from memory.memory import remember, recall


def execute(intent, params):
    if intent == "remember":
        remember(params["key"], params["value"])
    elif intent == "recall":
        value = recall(params["key"])
        return value
    elif intent == "open_app":
        print("DEBUG -> App to open:", params["app"])
        open_app(params["app"])
    elif intent == "search":
        search_google(params["query"])
    elif intent == "open_website":
        open_website(params["url"])
    elif intent == "play_media":
        print("DEBUG -> Media query:", params["query"])
        play_youtube(params["query"])
    elif intent == "play_media_advanced":
        print("DEBUG -> Automation query:", params["query"])
        play_youtube_advanced(params["query"])
