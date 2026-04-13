from agents.execution import execute
from agents.automation_agent import run_automation_agent
from agents.code_agent import run_code_agent
from agents.memory_agent import run_memory_agent
from agents.system_agent import run_system_agent
from agents.web_agent import run_web_agent


def dispatch(agent, command):
    if agent == "code_agent":
        return run_code_agent(command)

    if agent == "memory_agent":
        return run_memory_agent(command)
    if agent == "automation_agent":
        return run_automation_agent(command)
    if agent == "web_agent":
        return run_web_agent(command)
    if agent == "system_agent":
        return run_system_agent(command)
    return execute("analyze_context", {"query": command})
