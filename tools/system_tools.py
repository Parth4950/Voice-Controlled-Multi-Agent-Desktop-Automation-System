import os
import subprocess
import webbrowser
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tools.browser import get_driver

APP_MAP = {
    "chrome": r"C:\Users\chand\AppData\Local\Google\Chrome\Application\chrome.exe",
    "google chrome": r"C:\Users\chand\AppData\Local\Google\Chrome\Application\chrome.exe",

    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",

    "file explorer": "explorer",
    "explorer": "explorer",

    "vscode": "code",
    "visual studio code": "code",

    "spotify": r"C:\Users\chand\AppData\Local\Microsoft\WindowsApps\Spotify.exe",

    "youtube": "https://www.youtube.com",
    "netflix": "https://www.netflix.com",
}

APP_FALLBACKS = {
    "spotify": [
        r"C:\Users\chand\AppData\Roaming\Spotify\Spotify.exe",
        r"C:\Users\chand\AppData\Local\Microsoft\WindowsApps\Spotify.exe",
        "spotify:",
    ],
    "vscode": [
        r"C:\Users\chand\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        "code",
    ],
    "cursor": [
        r"C:\Users\chand\AppData\Local\Programs\Cursor\Cursor.exe",
        r"C:\Program Files\Cursor\Cursor.exe",
    ],
    "whatsapp": [
        r"C:\Users\chand\AppData\Local\WhatsApp\WhatsApp.exe",
        r"C:\Users\chand\AppData\Local\Microsoft\WindowsApps\WhatsApp.exe",
        "whatsapp:",
    ],
    "file explorer": [r"C:\Windows\explorer.exe"],
    "explorer": [r"C:\Windows\explorer.exe"],
    "haveloc": [r"C:\Program Files\Haveloc\Haveloc.exe"],
}


def open_app(app_name):
    try:
        app_name = app_name.lower().strip()
        mapped = APP_MAP.get(app_name)
        if mapped is None:
            print("Bruh, I don’t know this app yet")
            return

        print("DEBUG -> Launching:", mapped)

        if mapped.startswith("http"):
            webbrowser.open(mapped)
            return

        is_full_path = os.path.isabs(mapped) or ("\\" in mapped) or ("/" in mapped)
        if is_full_path:
            if os.path.exists(mapped):
                os.startfile(mapped)
            else:
                print("Bruh, path not found:", mapped)
            return

        subprocess.Popen(mapped, shell=True)
    except Exception:
        print(f"Could not open app: {app_name}")


def search_google(query):
    webbrowser.open(f"https://www.google.com/search?q={query}")


def open_website(url):
    webbrowser.open(url)


def play_youtube(query):
    webbrowser.open(f"https://www.youtube.com/results?search_query={query}")


def play_youtube_automated(query):
    query = query.strip()
    if query.lower().startswith("play "):
        query = query[5:].strip()

    try:
        print(f"Automating on YouTube: {query}")
        driver = get_driver()
        if driver is None:
            raise RuntimeError("Selenium driver is not available")

        driver.get("https://www.youtube.com")
        wait = WebDriverWait(driver, 6)
        search_bar = wait.until(EC.presence_of_element_located((By.NAME, "search_query")))
        search_bar.clear()
        search_bar.send_keys(query)
        search_bar.send_keys(Keys.ENTER)

        first_video = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a#video-title")))
        first_video.click()
        print("DEBUG -> Opened first video with Selenium")
    except Exception as e:
        print(f"DEBUG -> Selenium fallback to fast mode: {e}")
        play_youtube(query)
