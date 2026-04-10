import pyttsx3


def speak(text):
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    selected_voice_id = None

    for voice in voices:
        name = (voice.name or "").lower()
        if "zira" in name:
            selected_voice_id = voice.id
            break

    if selected_voice_id:
        engine.setProperty("voice", selected_voice_id)
    elif voices:
        engine.setProperty("voice", voices[0].id)

    engine.say(text)
    engine.runAndWait()
