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
import os
import shlex
import argparse
import logging

CAMERA_NAME = "virtual_camera"
MIC_NAME = "virtual_mic"
driver = None
RUNNING = True
CAMERA_READY = False
ffplay_pid = None
ffmpeg_pid = None


def exit_program():
    logging.info("Exiting cam_integration!")
    global RUNNING
    RUNNING = False
    if ffplay_pid:
        try:
            os.kill(ffplay_pid, signal.SIGKILL)
        except OSError:
            logging.warning("ffplay could not be killed, "
                            "maybe already killed")
    if ffmpeg_pid:
        try:
            os.kill(ffmpeg_pid, signal.SIGKILL)
        except OSError:
            logging.warning("ffmpeg could not be killed, "
                            "maybe already killed")
    driver.quit()
    sys.exit(0)


def signal_handler(sig, frame):
    logging.info("Received SIGINT")
    exit_program()


def create_loopback_device(device_number, camera_name):
    """
    Uses the v4l2loopback module to create a virtual camera device
    Removes previous v4l2loopback modules, as only one can be active at a time
    """
    subprocess.run("sudo modprobe -r v4l2loopback", shell=True)
    time.sleep(1)
    subprocess.run(f'sudo modprobe v4l2loopback video_nr={device_number}'
                   f' card_label="{camera_name}" exclusive_caps=1', shell=True)
    time.sleep(1)


def manage_ffmpeg(video_stream, audio_stream, device_number):
    """
    Starts the ffmpeg proess to retrieve the rtsp stream
    Monitors the cpu usage of the ffmpeg process and restarts it if needed
    """
    global ffmpeg_pid
    global ffplay_pid

    if video_stream:
        ffmpeg_pid = get_video_stream(video_stream, device_number)
    if audio_stream:
        ffplay_pid = get_audio_stream(audio_stream)

    while RUNNING:
        if video_stream and not monitor_process(ffmpeg_pid, 1.0):
            logging.error("Restarting ffmpeg!")
            try:
                os.kill(ffmpeg_pid, signal.SIGKILL)
            except OSError:
                logging.warning("ffmpeg could not be killed, "
                                "maybe already killed")
            ffmpeg_pid = get_video_stream(video_stream, device_number)

        if audio_stream and not monitor_process(ffplay_pid, 1.0):
            logging.error("Restarting ffplay!")
            try:
                os.kill(ffplay_pid, signal.SIGKILL)
            except OSError:
                logging.warning("ffplay could not be killed, "
                                "maybe already killed")
            ffplay_pid = get_audio_stream(audio_stream)
        time.sleep(10)
    if ffmpeg_pid:
        try:
            os.kill(ffmpeg_pid, signal.SIGKILL)
        except OSError:
            logging.warning("ffmpeg could not be killed, "
                            "maybe already killed")
    if ffplay_pid:
        try:
            os.kill(ffplay_pid, signal.SIGKILL)
        except OSError:
            logging.warning("ffplay could not be killed, "
                            "maybe already killed")


def monitor_process(pid, threshold):
    """
    Uses pidstat to monitor the current cpu usage of the process
    If it is under the threshold, False is returned
    """
    logging.debug(f"Monitoring {pid}!")
    monitoring_command = f"pidstat -p {pid} 3 1 | tail -1 | awk '{{print $8}}'"
    monitoring_result = subprocess.run(monitoring_command, shell=True,
                                       capture_output=True, text=True)

    try:
        cpu_usage = float(monitoring_result.stdout.replace(",", "."))
    except ValueError:
        return False
    logging.debug(cpu_usage)

    if cpu_usage < threshold:
        logging.error(f"There is a problem with process {pid}!")
        return False

    return True


def get_video_stream(stream_url, device_number):
    """
    Uses ffmpeg to retrieve the rtsp stream and
    play it into the virtual camera device
    """
    command = f"ffmpeg -loglevel error -rtsp_transport tcp -i {stream_url} -f"\
              f" v4l2 -vcodec rawvideo -pix_fmt yuv420p"\
              f" /dev/video{device_number}"
    if RUNNING:
        ffmpeg_proc = subprocess.Popen(shlex.split(command),
                                       stdin=subprocess.PIPE, shell=False)
    else:
        return None

    result = None
    while RUNNING:
        result = subprocess.run("v4l2-ctl --device=10 --all | "
                                "grep 'Size Image' head -1 |awk '{print $4}'",
                                capture_output=True, shell=True)
        logging.debug(f"Current size image: {result.stdout}")
        if result.stdout != b"0\n":
            break
        time.sleep(1)

    logging.debug(f"Result of v4l2-ctl command: {result.stdout}")

    global CAMERA_READY
    CAMERA_READY = True

    logging.info(f"ffmpeg PID: {ffmpeg_proc.pid}")

    return ffmpeg_proc.pid


def get_audio_stream(stream_url):
    """
    Uses ffplay to play the sound of the rtsp stream
    This sound should be picked up by the virtual mic
    """
    command = f"ffplay -loglevel error -rtsp_transport"\
              f" tcp -nodisp {stream_url}"
    if RUNNING:
        ffplay_proc = subprocess.Popen(shlex.split(command), shell=False)
    else:
        return None
    logging.info(f"ffplay PID: {ffplay_proc.pid}")

    return ffplay_proc.pid


def create_virtual_mic(microphone_name):
    subprocess.run("pactl unload-module module-remap-source", shell=True)
    subprocess.run("pactl unload-module module-null-sink", shell=True)

    null_sink_cmd = "pactl load-module module-null-sink sink_name=virtmic"\
                    " sink_properties=device.description="\
                    "Virtual_Microphone_Sink"
    module_null_sink_output = subprocess.run(null_sink_cmd, shell=True,
                                             capture_output=True, text=True)

    remap_source_cmd = f"pactl load-module module-remap-source master=virtmic"\
                       f".monitor source_name=virtmic source_properties="\
                       f"device.description={microphone_name}"
    module_remap_source_output = subprocess.run(remap_source_cmd, shell=True,
                                                capture_output=True, text=True)

    logging.info(f"module-null-sink: {module_null_sink_output.stdout}")
    logging.info(f"module-remap-source: {module_remap_source_output.stdout}")


def wait_for(element, timeout=10):
    """Waits for an element to be located and clickable."""
    WebDriverWait(driver, timeout).until(
            expected_conditions.presence_of_element_located(element))
    WebDriverWait(driver, timeout).until(expected_conditions
                                         .element_to_be_clickable(element))


def click_button_xpath(button_xpath):
    """Clicks button given by the xpath of the button."""
    try:
        # wait for button to be clickable and the cllick it
        wait_for((By.XPATH, button_xpath))
        element = driver.find_element(by=By.XPATH, value=button_xpath)
        driver.execute_script("arguments[0].click();", element)
    except NoSuchElementException:
        logging.critical(f"Button with XPath: {button_xpath} "
                         "not found! Aborting.")
        driver.quit()
        exit(-1)


def fill_input_xpath(input_xpath, input):
    """Fills the input field given by its xpath with input."""
    try:
        # wait for input field to be available and the fill it with the input
        wait_for((By.XPATH, input_xpath))
        driver.find_element(by=By.XPATH, value=input_xpath).send_keys(input)
    except NoSuchElementException:
        logging.critical(f"Input with XPath: {input_xpath} not found! "
                         "Aborting.")
        driver.quit()
        exit(-1)


def select_option(select_xpath, option_text):
    """
    Selects option given by option_text in dropdown menu given by its xpath
    """
    wait_for((By.XPATH, select_xpath))
    select = Select(driver.find_element(by=By.XPATH, value=select_xpath))
    select.select_by_visible_text(option_text)


def select_last_option(select_xpath):
    """Selects last option in dropdown menu given by its xpath"""
    wait_for((By.XPATH, select_xpath))
    select = Select(driver.find_element(by=By.XPATH, value=select_xpath))
    num_options = len(select.options)
    select.select_by_index(num_options - 1)


def integrate_camera(room_url, id, infrastructure, video_stream, audio_stream):
    logging.debug(f"video stream: {video_stream}")
    logging.debug(f"audio stream: {audio_stream}")
    # create and initialize audio resources
    if audio_stream:
        create_virtual_mic(MIC_NAME)

    # initialize video resources, i.e., the virtual device and ffmpeg process
    if video_stream:
        create_loopback_device(10, CAMERA_NAME)
    ffmpeg_thread = threading.Thread(target=manage_ffmpeg,
                                     args=(video_stream, audio_stream, 10))
    ffmpeg_thread.start()

    time.sleep(5)

    # get chrome options and add argument for granting camera permission
    # and window maximization
    options = webdriver.ChromeOptions()
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--start-maximized")
    options.add_argument("--headless")

    global driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                              options=options)

    # go to initial website
    driver.get(room_url)

    time.sleep(1)

    if infrastructure == "greenlight":

        # get field for entering the name of the user
        enterName_xpath = '//*[@placeholder="Enter your name!"]'
        fill_input_xpath(enterName_xpath, id)

        time.sleep(1)

        # click the join button to join the meeting
        joinRoom_xpath = '//*[@id="room-join"]'
        click_button_xpath(joinRoom_xpath)

        time.sleep(3)

    elif infrastructure == "studip":
        enterName_xpath = '//*[@name="name"]'
        fill_input_xpath(enterName_xpath, id)

        time.sleep(1)

        # click the join button to join the meeting
        joinRoom_xpath = '//*[@name="accept"]'
        click_button_xpath(joinRoom_xpath)

        time.sleep(3)

    else:
        logging.critical("Wrong infrastructure parameter set!")
        exit_program()

    # if the meeting is not started yet, the url does not change
    # therefore wait until url changes
    while driver.current_url == room_url:
        logging.warning("Waiting for meeting to start!")
        time.sleep(5)

    time.sleep(1)

    # go into listen only mode
    # listenOnly_xpath ='//*[@class="icon--2q1XXw icon-bbb-listen"]'
    # click_button_xpath(listenOnly_xpath)

    if audio_stream:
        # activate microphone
        microphone_xpath = '//*[@aria-label="Microphone"]'
        click_button_xpath(microphone_xpath)
    else:
        # go into listen only mode
        listenOnly_xpath = '//*[@aria-label="Listen only"]'
        click_button_xpath(listenOnly_xpath)

    time.sleep(10)

    if video_stream:
        while not CAMERA_READY:
            time.sleep(1)

    # click the share camera button to open the sharing dialogue
    if video_stream:
        shareCamera_xpath = '//*[@aria-label="Share webcam"]'
        click_button_xpath(shareCamera_xpath)
        time.sleep(5)

        # select the virtual camera for sharing
        selectCamera_xpath = '//*[@id="setCam"]'
        select_option(selectCamera_xpath, CAMERA_NAME)
        time.sleep(2)

        # for now, dont take highest quality video,
        # since this makes the system more error-prone
        # #select video quality for sharing the camera
        # selectQuality_xpath = '//*[@id="setQuality"]'
        # select_last_option(selectQuality_xpath)
        # time.sleep(3)

        # start sharing the camera
        startSharing_xPath = '//*[@aria-label="Start sharing"]'
        click_button_xpath(startSharing_xPath)
        time.sleep(1)

    if audio_stream:
        # expand list for changing audio devices
        changeAudioDevice_xpath = '//*[@aria-label="Change audio device"]'
        click_button_xpath(changeAudioDevice_xpath)
        time.sleep(1)

        # choose virtual microphone by its given name
        micname_xpath = f"//*[contains(text(),'{MIC_NAME}')]"
        click_button_xpath(micname_xpath)

    time.sleep(100)

    driver.quit()
    global RUNNING
    RUNNING = False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename="cam_integration.log",
                        filemode="w",
                        format="%(asctime)s - %(levelname)s - %(message)s")

    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser()

    parser.add_argument("room_url", help="URL of the meeting room")
    parser.add_argument("id", help="Name to be displayed in the meeting")
    parser.add_argument("infrastructure",
                        help="Infrastructure used for the meeting room")
    parser.add_argument("--audio", help="URL of the audio stream")
    parser.add_argument("--video", help="URL of the video stream")

    args = parser.parse_args()

    room_url = args.room_url
    id = args.id
    infrastructure = args.infrastructure
    audio_stream = args.audio
    video_stream = args.video

    integrate_camera(room_url, id, infrastructure, video_stream, audio_stream)
