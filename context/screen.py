import pyautogui
import pytesseract
from PIL import Image


def capture_screen():
    screenshot = pyautogui.screenshot()
    screenshot.save("screen.png")
    print("DEBUG -> Screenshot captured")
    return "screen.png"


def extract_text(image_path):
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    print("DEBUG -> Extracted text:", text)
    return text
