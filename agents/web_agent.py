from ai.gemini import ask_gemini
from memory.context import update_context, get_context


def run_web_agent(command):
    ctx = get_context()

    prompt = f"""
   You are a helpful AI assistant.

   Previous context:
   {ctx}

   User question:
   {command}

   Give a clear, concise, and accurate explanation.
   If it is a technical topic, explain in simple terms.
   """

    response = ask_gemini(prompt)
    update_context(command=command, response=response)
    return response
