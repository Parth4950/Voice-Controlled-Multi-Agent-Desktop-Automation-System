from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

driver = None


def get_driver():
    global driver

    if driver:
        return driver

    options = Options()

    options.add_argument(
        "user-data-dir=C:\\Users\\chand\\AppData\\Local\\Google\\Chrome\\BruhProfile"
    )

    options.add_argument("--start-maximized")

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        return driver

    except Exception as e:
        print("DEBUG -> Selenium failed:", e)
        return None
