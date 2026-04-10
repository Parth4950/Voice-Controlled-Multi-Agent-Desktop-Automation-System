from agents.router import route_command
from agents.execution import execute
from voice.input import listen_command
from voice.output import speak


while True:
    typed_mode = False
    command = listen_command()
    if not command:
        typed = input("Type command (or press Enter to keep listening): ").strip().lower()
        if not typed:
            continue
        command = typed
        typed_mode = True

    print(f"Heard: {command}")

    if not typed_mode and "bro" not in command:
        continue

    if "bro" in command:
        command = command.replace("bro", "", 1).strip()
    if not command:
        continue

    commands_list = command.split(" and ")
    interaction_keywords = ("click", "first", "control", "interact", "automate", "auto")
    has_interaction_step = any(
        any(keyword in cmd for keyword in interaction_keywords) for cmd in commands_list
    )

    for cmd in commands_list:
        intent, params = route_command(cmd)

        if intent == "play_media" and has_interaction_step:
            intent = "play_media_advanced"

        if intent == "unknown" and any(keyword in cmd for keyword in interaction_keywords):
            continue

        if intent == "unknown":
            print(f"Bruh, I didn’t understand: {cmd}")
            speak("Bruh, I didn’t understand that")
        else:
            result = execute(intent, params)
            if intent == "remember":
                speak("Got it, I’ll remember that")
            elif intent == "recall":
                key = params["key"]
                if result:
                    speak(f"Your {key} is {result}")
                else:
                    speak("I don’t know that yet")
            elif intent == "open_app":
                speak("Opening application")
            elif intent == "search":
                speak("Searching now")
            elif intent == "play_media":
                speak("Playing on YouTube")
            elif intent == "play_media_advanced":
                speak("Playing and controlling video")