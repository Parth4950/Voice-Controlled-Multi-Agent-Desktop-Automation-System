from agents.execution import execute


def run_automation_agent(command):
    query = command.lower()
    for word in ["play", "search", "automate"]:
        query = query.replace(word, "")
    query = " ".join(query.split())

    execute("play_media_advanced", {"query": query})
    return "Automating task now"
