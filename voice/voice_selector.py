import json
import os

import pyttsx3


def main():
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    sample_text = "Hey bro, this is how I sound."

    if not voices:
        print("No voices found.")
        return

    print("Available voices:")
    for index, voice in enumerate(voices):
        print(f"{index}: {voice.name} ({voice.id})")

    print("\nPreviewing voices...")
    for index, voice in enumerate(voices):
        print(f"\nPreview {index}: {voice.name}")
        engine.setProperty("voice", voice.id)
        engine.say(sample_text)
        engine.runAndWait()

    choice = input("\nEnter the index of the voice you want to keep: ").strip()
    if not choice.isdigit():
        print("Invalid choice.")
        return

    selected_index = int(choice)
    if selected_index < 0 or selected_index >= len(voices):
        print("Index out of range.")
        return

    selected_voice = voices[selected_index]
    config_path = os.path.join(os.path.dirname(__file__), "voice_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"voice_id": selected_voice.id}, f, indent=2)

    print(f"Saved voice: {selected_voice.name}")


if __name__ == "__main__":
    main()
