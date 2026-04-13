context = {
    "last_command": None,
    "last_response": None,
    "last_screen_text": None
}


def update_context(command=None, response=None, screen_text=None):
    if command is not None:
        context["last_command"] = command
    if response is not None:
        context["last_response"] = response
    if screen_text is not None:
        context["last_screen_text"] = screen_text


def get_context():
    return context
