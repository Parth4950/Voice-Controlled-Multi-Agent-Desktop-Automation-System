from agents.router import route_command
from agents.execution import execute
from agents.planner import plan_task
from agents.dispatcher import dispatch
import time
from voice.input import listen_command
from voice.output import speak


def is_simple_command(command):
    keywords = ["open", "search", "play"]
    return any(command.startswith(k) for k in keywords)


session_active = False


while True:
    try:
        try:
            command = listen_command()
        except Exception:
            continue

        if not command:
            continue

        print("DEBUG -> Heard command:", command)

        if not session_active:
            if "hey bro" in command.lower():
                session_active = True
                speak("Hey Parth, what can I do for you today?")
            continue

        if session_active:
            if not command:
                continue
            command = command.lower().strip()

            # EXIT
            if "bye" in command:
                speak("Alright, see you!")
                session_active = False
                continue

            # IGNORE SHORT NOISE
            if len(command.split()) < 3:
                continue

            interaction_keywords = ("click", "first", "control", "interact", "automate", "auto")
            has_interaction_step = any(keyword in command for keyword in interaction_keywords)

            print("DEBUG -> Checking fast path")

            # FAST PATH
            if is_simple_command(command):
                print("DEBUG -> Fast path triggered")
                intent, params = route_command(command)
                if intent == "play_media" and has_interaction_step:
                    intent = "play_media_advanced"
                execute(intent, params)
                continue

            # AI PATH
            print("DEBUG -> Going to AI path")
            agent = plan_task(command)
            valid_agents = {
                "code_agent",
                "web_agent",
                "system_agent",
                "automation_agent",
                "memory_agent",
            }
            if agent not in valid_agents:
                agent = "web_agent"

            print("DEBUG -> Selected agent:", agent)

            print("DEBUG -> Dispatching to agent")
            response = dispatch(agent, command)

            print("DEBUG -> Response received:", response)

            if response:
                print("Bruh:", response)
                speak(response[:300])

    except Exception:
        continue
    finally:
        time.sleep(0.5)
