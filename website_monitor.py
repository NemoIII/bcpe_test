import time
import logging
import traceback
import pyautogui

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from PIL import ImageGrab
import xml.etree.ElementTree as ET

# Setup logging
logging.basicConfig(
    filename="website_monitor.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def read_config():
    tree = ET.parse("param.xml")
    root = tree.getroot()
    website_url = root.find("website_url").text
    browser_choice = root.find("browser").text
    location = root.find("location").text
    return website_url, browser_choice, location


def take_screenshot(name="screenshot"):
    """Capture screenshot in case of errors"""
    try:
        screenshot = ImageGrab.grab()
        screenshot.save(f"images/{name}.png")
    except Exception as e:
        logging.error(f"Failed to take screenshot using ImageGrab: {str(e)}")
        pyautogui.screenshot(f"{name}_fallback.png")  # Fallback to pyautogui if needed


def monitor_website():
    website_url, browser_choice, location = read_config()

    # Choose browser (Chrome/Edge)
    if browser_choice == "chrome":
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        driver = webdriver.Chrome(
            service=Service("chromedriver-mac-arm64/chromedriver"),
            options=chrome_options,
        )
    else:
        # Edge Setup
        edge_options = Options()
        driver = webdriver.Edge(
            service=Service("path_to_edgedriver"), options=edge_options
        )

    try:
        # Step 1: Access URL
        driver.get(website_url)
        logging.info("Accessed the website")

        # Step 2: Handle Cookie Popup (if it exists)
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(text(), 'Tout accepter')]")
                )
            )
            accept_button = driver.find_element(
                By.XPATH, "//button[contains(text(), 'Tout accepter')]"
            )
            accept_button.click()
            logging.info("Accepted cookies")
        except (NoSuchElementException, TimeoutException):
            logging.info("No cookie popup found, continuing...")

        # Try closing any modal that might still be present
        try:
            close_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "js-close-dialog"))
            )
            close_button.click()
            logging.info("Closed the modal.")
        except TimeoutException:
            logging.info("No modal was found to close.")

        # Step 3: Ensure that no blocking modals are present before clicking the button
        try:
            # Wait until the modal is either invisible or removed from the DOM
            WebDriverWait(driver, 10).until(
                EC.staleness_of(
                    driver.find_element(By.CLASS_NAME, "bpce-modal-animate-container")
                )
            )
            logging.info("Modal is now removed or no longer affecting the page.")

            # Scroll to the element (if needed)
            find_agency_button = driver.find_element(By.LINK_TEXT, "Trouver une agence")
            driver.execute_script(
                "arguments[0].scrollIntoView(true);", find_agency_button
            )

            # Log the state of the button before attempting the click
            logging.info(
                f"Button state: displayed={find_agency_button.is_displayed()}, enabled={find_agency_button.is_enabled()}"
            )

            # Check if the button is visible and enabled
            if find_agency_button.is_displayed() and find_agency_button.is_enabled():
                # Wait until the element is clickable
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Trouver une agence"))
                )
                time.sleep(2)  # Add a short delay to ensure stability
                find_agency_button.click()
                logging.info("Clicked on 'Find an agency'")
            else:
                raise Exception("Find an agency button is not visible or not enabled.")

        except Exception as e:
            logging.error(
                f"Error occurred while clicking 'Trouver une agence': {str(e)}"
            )
            take_screenshot("error_find_agency")

        # Step 4: Fill form with 'Lyon' and search
        try:
            # Wait for the 'Rue' field to be visible and enter the location
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "font-text-body-bold"))
            )
            search_input.send_keys("Lyon")

            # Try to locate the ZIP input field by ID
            try:
                zip_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "em-searchcity"))
                )
                logging.info("ZIP input field found.")
            except TimeoutException:
                logging.error("Failed to find ZIP input field by ID, trying alternative locator.")
                zip_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Ville / Code postal']"))
                )

            zip_input.send_keys("69000")

            # Wait for the search button to be clickable and click it
            search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Rechercher')]")
                )
            )
            search_button.click()
            logging.info("Searched for Lyon Perrache location")
        except NoSuchElementException as e:
            logging.error(f"Error locating form fields: {str(e)}")
            take_screenshot("error_form_fields")

        # Step 5: Choose 'Lyon Perrache' and click
        location_link = driver.find_element(By.LINK_TEXT, location)
        location_link.click()
        logging.info(f"Selected location: {location}")

        # Step 6: Verify location page or take diagnostics if errors
        time.sleep(2)
        if "Perrache" not in driver.page_source:
            raise Exception("Location page not loaded properly")
        logging.info("Verified location page")

    except Exception as e:
        # Global error handling: log error and capture screenshot
        logging.error(f"Error occurred: {str(e)}")
        logging.error(traceback.format_exc())  # Log full stack trace
        take_screenshot("error_screenshot")
        pyautogui.screenshot("error.png")

    finally:
        driver.quit()
        logging.info("Closed the browser")


if __name__ == "__main__":
    monitor_website()
