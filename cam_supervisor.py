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

hostname = "bbb-cam.vm.elan.codes"
active_process = None
TESTING = False


class stream_config:
    video_and_audio, video_only, audio_only = range(3)


def exit_program():
    logging.error("Exiting cam_supervisor!")
    if active_process:
        try:
            os.kill(active_process[1].pid, signal.SIGINT)
        except OSError:
            logging.warning("cam_supervisor could not be killed, "
                            "maybe already killed")
    sys.exit(0)


def signal_handler(sig, frame):
    exit_program()


def get_yaml(address, auth):
    if TESTING:
        with open("config.yaml") as file:
            return yaml.load(file, Loader=yaml.FullLoader)

    r = requests.get(address, auth=auth)

    if r.status_code == 200:
        logging.info("Successfully retrieved config yaml!")
        return yaml.load(r.text, Loader=yaml.CLoader)
    else:
        logging.warning("Could not get config yaml!")
        return None


def get_schedule(yml):
    return yml["clients"][hostname]["schedule"]


def check_schedule(schedule):
    """Returns schedule entry that should be active, or None if none exist"""
    for entry in schedule:
        if check_entry(entry, True):
            return entry
    return None


def check_entry(entry, bool):
    start_ts = parse(entry["start"]).timestamp()
    stop_ts = parse(entry["stop"]).timestamp()
    now_ts = time.time()

    if bool:
        now_ts = start_ts + 10  # ensure that time is in bounds on first entry

    if start_ts < now_ts and now_ts < stop_ts:
        return True
    else:
        return False


def start_process(entry):
    location = entry["location"]
    id = entry["id"]
    video = entry["video"]
    audio = entry["audio"]
    cwd = os.getcwd()
    infrastructure = get_infrastructure(yml, location)
    config = get_stream_config(entry)

    # just test
    # location = "https://bbb.elan-ev.de/b/art-gli-xx9-d2d"
    location = "https://studip.uni-osnabrueck.de/plugins.php/meetingplugin/"\
               "room/index/537f5cd0bb94922d836f2a784d34eda9/d9b4fba817373f7"\
               "17b3063b42961ec72?cancel_login=1"
    id = "42/201"
    video = "rtsp://rtsp.stream/pattern"
    audio = "rtsp://rtsp.stream/pattern"
    # video = "rtsp://131.173.172.32/mediainput/h264/stream_1"
    # audio = "rtsp://131.173.172.32/mediainput/h264/stream_1"
    infrastructure = get_infrastructure(yml, location)
    config = stream_config.video_and_audio
    # just test

    command = get_command(cwd, config, location, id,
                          video, audio, infrastructure)
    proc = subprocess.Popen(shlex.split(command), shell=False)
    global active_process
    active_process = (entry, proc)


def get_infrastructure(yml, room_url):
    """
    Returns type of infrastructure that is used for the room
    (returns'studip' or 'greenlight')
    """
    types = yml["infrastructure"]
    for prefix, infrastructure in types.items():
        if prefix in room_url:
            return infrastructure
    # if no infrastructure matches, abort
    logging.critical("No infrastructure matches the provided string!")
    exit_program()


def get_stream_config(entry):
    if entry["audio"] and entry["video"]:
        return stream_config.video_and_audio
    elif entry["video"]:
        return stream_config.video_only
    elif entry["audio"]:
        return stream_config.audio_only
    else:
        logging.critical("Either video or audio stream has to be provided!")
        exit_program()


def get_command(cwd, config, location, id, video, audio, infrastructure):
    if config == stream_config.video_and_audio:
        return f"python3 {cwd}/cam_integration.py {location} {id} "\
                  f"{infrastructure} --video {video} --audio {audio}"
    elif config == stream_config.video_only:
        return f"python3 {cwd}/cam_integration.py {location} {id} "\
                  f"{infrastructure} --video {video}"
    else:
        return f"python3 {cwd}/cam_integration.py {location} {id} "\
                  f"{infrastructure} --audio {audio}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename="cam_supervisor.log",
                        filemode="w",
                        format="%(asctime)s - %(levelname)s - %(message)s")

    signal.signal(signal.SIGINT, signal_handler)
    yaml_address = 'http://bbb-cam-config.vm.elan.codes/config.yml'
    yaml_auth = ('bbb-stream', 'bbb-stream')
    active_process = None

    while True:
        if active_process:
            if not check_entry(active_process[0], False):
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
            if newYml := get_yaml(yaml_address, yaml_auth):
                yml = newYml
            schedule = get_schedule(yml)

            if current_entry := check_schedule(schedule):
                start_process(current_entry)

        time.sleep(60)
