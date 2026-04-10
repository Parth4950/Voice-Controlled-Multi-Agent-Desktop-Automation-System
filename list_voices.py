import pyttsx3


engine = pyttsx3.init()
voices = engine.getProperty("voices")

for index, voice in enumerate(voices):
    print(f"Index: {index}")
    print(f"ID: {voice.id}")
    print(f"Name: {voice.name}")
    print("-" * 40)
