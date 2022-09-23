import os
import signal
import requests
import yaml
from dateutil.parser import *
import time
import subprocess
import shlex
import sys

hostname = "bbb-cam.vm.elan.codes"
active_process = None

def signal_handler(sig, frame):
    print("Exiting cam_supervisor!")
    if active_process:
        try:
            os.kill(active_process[1].pid, signal.SIGINT)
        except OSError:
            pass
    sys.exit(0)

def get_yaml(address, auth):
    r = requests.get(address, auth=auth)

    return yaml.load(r.text, Loader=yaml.CLoader)

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
        now_ts = start_ts + 10 #ensures that entry is within bounds on the first entry
        
    if start_ts < now_ts and now_ts < stop_ts:
        return True
    else:
        return False

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    yaml_address = 'http://bbb-cam-config.vm.elan.codes/config.yml'
    yaml_auth = ('bbb-stream', 'bbb-stream')
    active_process = None

    while True:
        if active_process:
            if not check_entry(active_process[0], False):
                print("Stop time for active process reached!")
                try:
                    os.kill(active_process[1].pid, signal.SIGINT)
                except OSError:
                    pass
                active_process = None

        else:    
            yml = get_yaml(yaml_address, yaml_auth)
            schedule = get_schedule(yml)

            current_entry = check_schedule(schedule)

            if current_entry:
                #print(current_entry)
                location = current_entry["location"]
                id = current_entry["id"]
                video = current_entry["video"]
                audio = current_entry["audio"]
                cwd = os.getcwd()

                ####just test
                ####
                location = "https://bbb.elan-ev.de/b/art-gli-xx9-d2d"
                id = "42/201"
                video = "rtsp://rtsp.stream/pattern"
                audio = "rtsp://rtsp.stream/pattern"
                ####
                proc = subprocess.Popen(shlex.split(f"python3 {cwd}/cam_integration.py {location} {id} {video} {audio}"), shell=False)
                active_process = (current_entry, proc)

        time.sleep(60)


    # cam_integration.integrate_camera("https://bbb.elan-ev.de/b/art-gli-xx9-d2d", "Virtual_Camera", "rtsp://rtsp.stream/pattern", "Virtual_Microphone")