"""
Load config yaml for the system, start and monitor cam_integration,
when a stream is scheduled
"""
import argparse
import os
import signal
import requests
import yaml
from dateutil.parser import parse
import time
import subprocess
import shlex
import sys
import logging
from typing import NoReturn
from types import FrameType
from enum import Enum

CONFIGURATION = None
active_process = None
PYTHON = "python3"


class stream_config(Enum):
    """
    Enum class for the stream config, indicating whether video/audio is used
    """
    video_and_audio, video_only, audio_only = range(3)


def exit_program() -> NoReturn:
    """
    Free all resources and exit the program

    Returns:
        NoReturn: Does not return, since the program exits
    """
    logging.info("Exiting cam_supervisor!")
    if active_process:
        try:
            os.kill(active_process[1].pid, signal.SIGINT)
        except OSError:
            logging.warning("cam_supervisor could not be killed, "
                            "maybe already killed")
    sys.exit(0)


def signal_handler(sig: int, frame: FrameType) -> None:
    """
    Gets called when SIGINT is sent to process, calls exit_program()

    Args:
        sig (int): Signal given to signal_handler, can only be SIGINT
        frame (FrameType): Execution frame
    """
    logging.info("Received SIGINT")
    exit_program()


def get_yaml() -> dict:
    """
    Get the config yaml for the stream system

    Args:
        address (str): Address to retrieve the yaml
        auth (tuple): Username and password in a tuple for basic auth

    Returns:
        dict: configuration yaml for the stream system
    """

    if CONFIGURATION.get("test_schedules"):
        logging.info("Loading schedules from test configuration.")
        with open(CONFIGURATION["test_schedules"], "r") as f:
            test_schedule = yaml.safe_load(f)
        return test_schedule

    r = requests.get(
        CONFIGURATION["schedule_url"],
        auth=(CONFIGURATION["schedule_basic_auth_user"],
              CONFIGURATION["schedule_basic_auth_password"])
    )

    if r.status_code == 200:
        logging.info("Successfully retrieved config yaml!")
        return yaml.safe_load(r.text)
    else:
        logging.warning("Could not get config yaml!")
        return {}


def get_schedule(yml: dict, instance_key: str) -> dict:
    """
    Return schedule for the current system

    Args:
        yml (dict): configuration yaml for the stream system

    Returns:
        dict: Schedule entry for the current machine
    """
    return yml["clients"][instance_key]["schedule"]


def check_schedule(schedule: dict) -> dict:
    """
    Check, if there is an entry in the schedule that should be active

    Args:
        schedule (dict): Schedule for streams (from the config yaml)

    Returns:
        dict: Entry that should be active, or None if no entry should be active
    """
    for entry in schedule:
        if check_entry(entry):
            return entry
    return {}


def check_entry(entry: dict) -> bool:
    """
    Check whether given entry should be active

    Args:
        entry (dict): Schedule entry in the config yaml

    Returns:
        bool: True, if entry should be active, False otherwise
    """
    start_ts = parse(entry["start"]).timestamp()
    stop_ts = parse(entry["stop"]).timestamp()
    now_ts = time.time()

    return start_ts < now_ts < stop_ts


def start_process(entry: dict) -> None:
    """
    Start the process for cam integration

    Args:
        entry (dict): Configuration to be used for the stream
    """
    location = entry["location"]
    name = entry["id"]
    video = entry["video"]
    audio = entry["audio"]
    cwd = os.getcwd()
    infrastructure = get_infrastructure(yml, location)
    config = get_stream_config(entry)
    access_code = entry.get("access_code")
    video_quality = entry.get("video_quality")

    command = get_command(cwd, config, location, name,
                          video, audio, infrastructure, access_code,
                          video_quality)
    proc = subprocess.Popen(shlex.split(command), shell=False)
    global active_process
    active_process = (entry, proc)


def get_infrastructure(yml: dict, room_url: str) -> str:
    """
    Returns type of infrastructure that is used for the room

    Args:
        yml (dict): configuration yaml for the stream system
        room_url (str): url of a meeting room

    Returns:
        str: Can currently be "greenlight" or "studip"
    """
    types = yml["infrastructure"]
    for prefix, infrastructure in types.items():
        if prefix in room_url:
            return infrastructure
    # if no infrastructure matches, abort
    logging.critical("No infrastructure matches the provided string!")
    exit_program()


def get_stream_config(entry: dict) -> stream_config:
    """
    Get stream config describing whether video/audio streams are provided

    Args:
        entry (dict): Entry in the yaml describing the stream parameters

    Returns:
        stream_config: The stream config for the entry
    """
    if entry["audio"] and entry["video"]:
        return stream_config.video_and_audio
    elif entry["video"]:
        return stream_config.video_only
    elif entry["audio"]:
        return stream_config.audio_only
    else:
        logging.critical("Either video or audio stream has to be provided!")
        exit_program()


def get_command(cwd: str, config: str, location: str, name: str, video: str,
                audio: str, infrastructure: str, access_code: str,
                video_quality: str) -> str:
    """
    Construct command for starting cam integration

    Args:
        cwd (str): Current working directory
        config (stream_config): Describes whether audio/video should be used
        location (str): URL of the meeting room
        name (str): Name to be displayed in the meeting
        video (str): URL for video stream
        audio (str): URL for audio stream
        infrastructure (str): Infrastructure used for the meeting room
        access_code (str): Access code for joining as moderator
        video_quality (str): Video quality to select for the stream

    Returns:
        str: Command for starting the cam integration
    """
    if config == stream_config.video_and_audio:
        command = f"{PYTHON} {cwd}/cam_integration.py {location} {name} "\
                  f"{infrastructure} --video {video} --audio {audio}"
    elif config == stream_config.video_only:
        command = f"{PYTHON} {cwd}/cam_integration.py {location} {name} "\
                  f"{infrastructure} --video {video}"
    else:
        command = f"{PYTHON} {cwd}/cam_integration.py {location} {name} "\
                  f"{infrastructure} --audio {audio}"

    if access_code:
        command += f" --code {access_code}"
    if video_quality:
        command += f" --video_quality {video_quality}"

    return command


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename="cam_supervisor.log",
                        filemode="a",
                        format="%(asctime)s - %(levelname)s - %(message)s")

    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="service_configuration.yml",
                        type=str, help="path to the config file")
    parser.add_argument("-t", "--test-schedules", dest="testing", type=str,
                        help="path to a local file with test schedules")
    args = parser.parse_args()

    with open(args.config, 'r') as file:
        CONFIGURATION = yaml.safe_load(file)

    if args.testing:
        CONFIGURATION["test_schedules"] = args.testing

    active_process = None
    while True:
        if active_process:
            if not check_entry(active_process[0]):
                logging.info("Stop time for active process reached!")
                try:
                    os.kill(active_process[1].pid, signal.SIGINT)
                except OSError:
                    logging.warning("Active process could not be killed, "
                                    "maybe already killed")
                active_process = None
            elif active_process[1].poll() is not None:
                logging.error("Restarting active process!")
                start_process(active_process[0])
        else:
            if newYml := get_yaml():
                yml = newYml
            schedule = get_schedule(
                yml, CONFIGURATION["schedule_instance_key"]
            )

            if current_entry := check_schedule(schedule):
                start_process(current_entry)

        time.sleep(60)
