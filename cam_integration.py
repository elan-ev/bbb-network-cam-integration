from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions

import sys
import time


#set camera name
CAMERA_NAME = None
CHECK_AUDIO_DEVICES = False
driver = None


def wait_for(element, timeout=10):
    """Waits for an element to be located and clickable."""
    WebDriverWait(driver, timeout).until(
            expected_conditions.presence_of_element_located(element))
    WebDriverWait(driver, timeout).until(expected_conditions.element_to_be_clickable(element))


def click_button_xpath(button_xpath):
    """Clicks button given by the xpath of the button."""
    try:
        #wait for button to be clickable and the cllick it
        wait_for((By.XPATH, button_xpath))
        element = driver.find_element(by=By.XPATH, value=button_xpath)
        driver.execute_script("arguments[0].click();", element)
    except NoSuchElementException:
        print(f"Button with XPath: {button_xpath} not found! Aborting.")
        driver.quit()
        exit(-1)


def fill_input_xpath(input_xpath, input):
    """Fills the input field given by its xpath with input."""
    try:
        #wait for input field to be available and the fill it with the input
        wait_for((By.XPATH, input_xpath))
        driver.find_element(by=By.XPATH, value=input_xpath).send_keys(input)
    except NoSuchElementException:
        print(f"Input with XPath: {input_xpath} not found! Aborting.")
        driver.quit()
        exit(-1)


def select_option(select_xpath, option_text):
    """Selects option given by option_text in dropdown menu given by its xpath"""
    wait_for((By.XPATH, select_xpath))
    select = Select(driver.find_element(by=By.XPATH, value=select_xpath))
    select.select_by_visible_text(option_text)


def select_last_option(select_xpath):
    """Selects last option in dropdown menu given by its xpath"""
    wait_for((By.XPATH, select_xpath))
    select = Select(driver.find_element(by=By.XPATH, value=select_xpath))
    num_options = len(select.options)
    select.select_by_index(num_options - 1)


if __name__ == "__main__":

    ROOM_URL = sys.argv[1]
    HEADLESS = (sys.argv[2].lower() == "true")
    CAMERA_NAME = sys.argv[3]
    MIC_NAME = sys.argv[4]

    print(CAMERA_NAME)
    time.sleep(5)

    #get chrome options and add argument for granting camera permission and window maximization
    options = webdriver.ChromeOptions()
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--start-maximized")
    if HEADLESS:
        options.add_argument("--headless")
    
    # options.set_preference("media.navigator.permission.disabled", True)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    #go to initial website 
    driver.get(ROOM_URL)

    time.sleep(1)

    #get field for entering the name of the user
    enterName_xpath = '//*[@placeholder="Enter your name!"]'
    fill_input_xpath(enterName_xpath, "Camera and Audio")

    time.sleep(1)

    #click the join button to join the meeting
    joinRoom_xpath = '//*[@id="room-join"]'
    click_button_xpath(joinRoom_xpath)

    time.sleep(3)

    #if the meeting is not started yet, the url does not change, therefore wait until url changes
    while driver.current_url == ROOM_URL:
        print("Waiting for meeting to start!")
        time.sleep(5)

    time.sleep(1)


    # #go into listen only mode
    # listenOnly_xpath ='//*[@class="icon--2q1XXw icon-bbb-listen"]'
    # click_button_xpath(listenOnly_xpath)

    #activate speakers
    microphone_xpath = '//*[@aria-label="Microphone"]'
    click_button_xpath(microphone_xpath)


    time.sleep(3)
    
    if CHECK_AUDIO_DEVICES:
        #expand list for changing audio devices
        changeAudioDevice_xpath = '//*[@aria-label="Change audio device"]'
        click_button_xpath(changeAudioDevice_xpath)

        time.sleep(3)

        #take screenshot to see, whether devices are listed. In headless mode in firefox,
        #devices are not displayed. In normal mode or in chrome, they are.
        driver.save_screenshot("./Screenshots/microphoneList.png")
        driver.quit()
        exit(0)

    shareCamera_xpath = '//*[@aria-label="Share webcam"]'
    click_button_xpath(shareCamera_xpath)

    time.sleep(3)

    #crashes here, if headless and microphone active
    driver.save_screenshot("./Screenshots/beforeSetCam.png")
    selectCamera_xpath = '//*[@id="setCam"]'
    select_option(selectCamera_xpath, CAMERA_NAME)

    time.sleep(1)

    selectQuality_xpath = '//*[@id="setQuality"]'
    select_last_option(selectQuality_xpath)
    time.sleep(1)

    startSharing_xPath = '//*[@aria-label="Start sharing"]'
    click_button_xpath(startSharing_xPath)

    time.sleep(1)

    #expand list for changing audio devices
    changeAudioDevice_xpath = '//*[@aria-label="Change audio device"]'
    click_button_xpath(changeAudioDevice_xpath)

    time.sleep(1)

    #choose virtual microphone by its given name
    roomname_xpath = f"//*[contains(text(),'{MIC_NAME}')]"
    click_button_xpath(roomname_xpath)

    time.sleep(100)

    driver.quit()
