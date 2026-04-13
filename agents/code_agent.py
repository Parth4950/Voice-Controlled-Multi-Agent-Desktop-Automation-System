from context.screen import capture_screen, extract_text
from ai.gemini import ask_gemini
from memory.context import update_context, get_context


def run_code_agent(command):
    ctx = get_context()
    reference_words = ("it", "this", "that")

    if any(word in command for word in reference_words) and ctx.get("last_screen_text"):
        text = ctx["last_screen_text"]
    else:
        image_path = capture_screen()
        text = extract_text(image_path)

    update_context(screen_text=text, command=command)

    prompt = f"""
   You are an expert software engineer.

   Previous context:
   {ctx}

   Screen content:
   {text}

   User query:
   {command}

   Explain clearly, debug issues, and give solutions.
   """

    response = ask_gemini(prompt)
    update_context(response=response)
    return response
