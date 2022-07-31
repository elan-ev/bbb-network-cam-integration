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


def room_exists(roomname):
    """Checks, whether the BBB room with the given name exists."""
    
    roomname_xpath = f"//*[contains(text(),'{roomname}')]"
    
    try:
        driver.find_element(by=By.XPATH, value=roomname_xpath)
    except NoSuchElementException: #room not found
        return False

    return True



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

    USERNAME = sys.argv[1]
    PASSWORD = sys.argv[2]
    ROOMNAME = sys.argv[3]
    HEADLESS = (sys.argv[4].lower() == "true")
    CAMERA_NAME = sys.argv[5]

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
    driver.get("https://bbb.elan-ev.de/b/signin")

    #fill the username and password fields
    username_xpath = '//*[@id="session_username"]'
    password_xpath = '//*[@id="session_password"]'
    fill_input_xpath(username_xpath, USERNAME)
    fill_input_xpath(password_xpath, PASSWORD)

    #get current url for checking the login success later
    login_url = driver.current_url
    
    #confirm login
    confirmSignIn_xpath = '//*[@value="Sign in"]'
    click_button_xpath(confirmSignIn_xpath)

    time.sleep(1)

    #if url didnt change, login was unsuccessful
    if(driver.current_url == login_url):
        print("Login failed!")
        driver.quit()
        exit(-1)

    #use room with given room name if it exists, otherwise create a new room
    if(room_exists(ROOMNAME)):
        #click on the room to select it
        selectExistingRoom_xpath = f"//*[contains(text(),'{ROOMNAME}')]"
        click_button_xpath(selectExistingRoom_xpath)

        #give the browser time to notice the change
        time.sleep(1)
        
        #join/start the meeting
        start_xpath = '//*[@class="btn btn-primary btn-block start-button float-right"]'
        click_button_xpath(start_xpath)
    else:
        #click on create room
        createRoom_xpath = '//*[@id="create-room-block"]/div/div[2]'
        click_button_xpath(createRoom_xpath)
        
        #set the room name 
        roomName_xpath = '//*[@id="create-room-name"]'
        fill_input_xpath(roomName_xpath, ROOMNAME)

        #join meeting automatically
        automaticJoin_xpath = '//*[@id="auto-join-label"]/span[2]'
        click_button_xpath(automaticJoin_xpath)

        #confirm room creation
        confirmCreation_xpath = '//*[@value="Create Room"]'
        click_button_xpath(confirmCreation_xpath)


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


    time.sleep(10)

    driver.quit()
