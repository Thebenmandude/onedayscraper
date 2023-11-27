import os
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service  # Corrected import for Edge WebDriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.edge.options import Options
from datetime import datetime
import time

def send_telegram_message(bot_token, chat_id, message):
    send_text = f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&parse_mode=Markdown&text={message}'
    response = requests.get(send_text)
    return response.json()

def scrape_website(driver, wait, link_last_seen):
    seen_links = set()
    previous_links = set()
    stop_counter = 0
    new_links_found = False

    while stop_counter < 10:
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(2)

        try:
            xpath_for_button = "//button[contains(translate(text(), '0123456789', ''), 'Shop more deals')]"
            show_more_button = driver.find_element(By.XPATH, xpath_for_button)
            driver.execute_script("arguments[0].scrollIntoView();", show_more_button)
            show_more_button.click()
        except NoSuchElementException:
            pass  # If the button is not found, do nothing

        keywords = ["samsung"]
        xpath_conditions = ["contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{}')".format(keyword.lower()) for keyword in keywords]
        xpath_keywords_condition = " or ".join(xpath_conditions)
        xpath_query = f"//span[number(substring-before(text(), '%')) > 70 or ({xpath_keywords_condition})]"

        current_iteration_links = set()

        elements = driver.find_elements(By.XPATH, xpath_query)
        for element in elements:
            section = element.find_element(By.XPATH, './ancestor::section')
            links = section.find_elements(By.XPATH, './/a[@href]')
            for link in links:
                href = link.get_attribute('href')
                current_iteration_links.add(href)
                if href not in seen_links:
                    seen_links.add(href)
                    print(href)

        if not current_iteration_links.issubset(previous_links):
            new_links_found = True
            for link in current_iteration_links - previous_links:
                seen_links.add(link)
                print(link)

        if current_iteration_links.issubset(previous_links):
            stop_counter += 1
            # print(f"No new unique links found. Incrementing stop_counter to {stop_counter}")
        else:
            stop_counter = 0
            # print("New unique links found. Resetting stop_counter.")

        previous_links.update(current_iteration_links)

    print(f"Number of unique links found: {len(seen_links)}")
    return new_links_found, seen_links

# Path to the Edge WebDriver executable
edge_driver_path = os.path.join(os.path.dirname( os.path.abspath(__file__)),"msedgedriver.exe")

# Create a Service object
service = Service(executable_path=edge_driver_path)

opt = Options()
opt.add_argument("--headless")

# Instantiate the Edge WebDriver with the Service object
driver = webdriver.Edge(service=service, options=opt)

# Set window size explicitly for headless mode
driver.set_window_size(1920, 1080)

# Navigate to the website
driver.get('https://www.onedayonly.co.za/')

# Wait for the page to load
wait = WebDriverWait(driver, 10)

# Telegram Bot Token and Chat ID
bot_token = ''
chat_id = ''

# Dictionary to track the last seen date of links
link_last_seen = {}

while True:
    new_links_found, unique_links = scrape_website(driver, wait, link_last_seen)
    current_date = datetime.now().date()

    if new_links_found:
        base_message_sent = False
        for link in unique_links:
            if link not in link_last_seen or link_last_seen[link] != current_date:
                if not base_message_sent:
                    base_message = f"New items found for {current_date}."
                    send_telegram_message(bot_token, chat_id, base_message)
                    base_message_sent = True
                send_telegram_message(bot_token, chat_id, link)
                link_last_seen[link] = current_date
    else:
        print("No new items found. No notification sent.")

    print("Waiting 5 minutes before restarting...")
    time.sleep(300)  # Wait for 5 minutes
    driver.refresh()
