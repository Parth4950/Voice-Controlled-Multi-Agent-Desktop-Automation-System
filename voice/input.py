import speech_recognition as sr

_MIC_ERROR_SHOWN = False


def listen_command():
    global _MIC_ERROR_SHOWN
    recognizer = sr.Recognizer()

    try:
        with sr.Microphone() as source:
            print("Listening...")
            audio = recognizer.listen(source)
    except Exception:
        if not _MIC_ERROR_SHOWN:
            print("Microphone is not available. Install PyAudio to use voice input.")
            _MIC_ERROR_SHOWN = True
        return ""

    try:
        text = recognizer.recognize_google(audio)
        return text.lower()
    except Exception:
        return ""
