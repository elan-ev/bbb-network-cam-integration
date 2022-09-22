import asyncio
from multiprocessing.sharedctypes import Value
import signal
import threading
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
import subprocess
import select
import os
import shlex

#set camera name
CAMERA_NAME = None
driver = None
RUNNING = True

def create_loopback_device(device_number, camera_name):
    """
    Uses the v4l2loopback module to create a virtual camera device
    Removes previous v4l2loopback modules, since only one can be active at a time
    """
    subprocess.run("sudo modprobe -r v4l2loopback", shell=True)
    time.sleep(1)
    subprocess.run(f'sudo modprobe v4l2loopback video_nr={device_number} card_label="{camera_name}" exclusive_caps=1', shell=True)
    time.sleep(1)

def manage_ffmpeg(stream_url, device_number):
    """
    Starts the ffmpeg proess to retrieve the rtsp stream
    Monitors the cpu usage of the ffmpeg process and restarts it if needed
    """
    pid = get_video_stream(stream_url, device_number)

    while RUNNING:
        if not monitor_process(pid, 1.0):
            print("Restarting ffmpeg!")
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
            pid = get_video_stream(stream_url, device_number)
        time.sleep(1)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass

def monitor_process(pid, threshold):
    """
    Uses pidstat to monitor the current cpu usage of the process
    If it is under the threshold, False is returned
    """
    print("Monitoring ffmpeg!")
    monitoring_command =  f"pidstat -p {pid} 1 1 | tail -1 | awk '{{print $8}}'"
    monitoring_result = subprocess.run(monitoring_command, shell=True, capture_output=True, text=True)
    
    try:
        cpu_usage = float(monitoring_result.stdout.replace(",","."))
    except ValueError:
        return False
    print(cpu_usage)

    if cpu_usage < threshold:
        print(f"There is a problem with process {pid}!")
        return False
    
    return True


def get_video_stream(stream_url, device_number):
    """
    Uses ffmpeg to retrieve the rtsp stream and play it into the virtual camera device
    """
    command = f"ffmpeg -rtsp_transport tcp -i {stream_url} -f v4l2 -vcodec rawvideo -pix_fmt yuv420p /dev/video{device_number}"
    print(command)

    ffmpeg_proc = subprocess.Popen(shlex.split(command), shell=False)

    print(f"PID: {ffmpeg_proc.pid}")

    return ffmpeg_proc.pid
    
def create_virtual_mic(microphone_name):
    subprocess.run("pactl unload-module module-remap-source", shell=True)
    subprocess.run("pactl unload-module module-null-sink", shell=True)
    subprocess.run("pactl load-module module-null-sink sink_name=virtmic sink_properties=device.description=Virtual_Microphone_Sink", shell=True)
    subprocess.run(f"pactl load-module module-remap-source master=virtmic.monitor source_name=virtmic source_properties=device.description={microphone_name}", shell=True)
    

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
    #get command line arguments for configuration of the program
    ROOM_URL = sys.argv[1]
    HEADLESS = (sys.argv[2].lower() == "true")
    CAMERA_NAME = sys.argv[3]
    RTSP_STREAM = sys.argv[4]
    MIC_NAME = sys.argv[5]

    #initialize video resources, i.e., the virtual device and the ffmpeg process
    create_loopback_device(10, CAMERA_NAME)
    ffmpeg_thread = threading.Thread(target=manage_ffmpeg, args=(RTSP_STREAM, 10))
    ffmpeg_thread.start()

    #create and initialize audio resources    
    create_virtual_mic(MIC_NAME)

    time.sleep(5)

    #get chrome options and add argument for granting camera permission and window maximization
    options = webdriver.ChromeOptions()
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--start-maximized")
    if HEADLESS:
        options.add_argument("--headless")
    
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
    time.sleep(6)


    #click the share camera button to open the sharing dialogue
    shareCamera_xpath = '//*[@aria-label="Share webcam"]'
    click_button_xpath(shareCamera_xpath)
    time.sleep(5)

    #select the virtual camera for sharing
    selectCamera_xpath = '//*[@id="setCam"]'
    select_option(selectCamera_xpath, CAMERA_NAME)
    time.sleep(2)

    #select video quality for sharing the camera
    selectQuality_xpath = '//*[@id="setQuality"]'
    select_last_option(selectQuality_xpath)
    time.sleep(3)

    #start sharing the camera
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
    
    RUNNING = False