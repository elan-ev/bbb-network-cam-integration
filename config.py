from importlib.resources import is_resource
from tabnanny import check
import PySimpleGUI as sg
import yaml
import os
import re
from validator_collection import checkers

regex ="^(2[0-3]|[01]?[0-9]):([0-5]?[0-9])$"

def validateTime(text):
    result = re.match(regex, text)
    if result is None or result.group() != text:
        return False
    else:
        return True

if __name__ == "__main__":
    layout = [
        [sg.Text("YAML file name:"), sg.InputText(key="-YAML_NAME-", size=(20,1)), sg.FileBrowse(initial_folder=os.getcwd(), file_types=[("YAML Files", "*.yaml")]), sg.Button("Load File")],
        [sg.Text("ROOM_URL:"), sg.Input(key="-ROOM_URL-", size=(50,1))],
        [sg.Text("RTSP_STREAM_URL:"), sg.Input(key="-RTSP_STREAM_URL-", size=(50,1))],
        [sg.Checkbox(text="Headless", default=True, key="-HEADLESS-")],
        [sg.OptionMenu(values=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], default_value="Mon", size=(5,1), key="-WEEKDAY-"), sg.Text("Start time:"), sg.Input(default_text="12:00", size=(5,0), key="-START-"), sg.Text("End time:"), sg.Input(default_text="14:00", size=(5,0), key="-END-")],
        [sg.Button("Confirm"), sg.Button("Cancel")]
    ]


    window = sg.Window(title="Config", layout=layout, margins=(500, 250))

    while True:
        event, values = window.read()

        YAML_FILE_NAME = values["-YAML_NAME-"]
        ROOM_URL = values["-ROOM_URL-"]
        RTSP_STREAM_URL = values["-RTSP_STREAM_URL-"]
        HEADLESS = values["-HEADLESS-"]
        WEEKDAY = values["-WEEKDAY-"]
        START = values["-START-"]
        END = values["-END-"]

        if event == "Cancel" or event == sg.WIN_CLOSED:
            break
        elif event == "Confirm":
            if not validateTime(START):
                print(f"{START} is not a valid start time!")
            elif not validateTime(END):
                print(f"{END} is not a valid end time!")

            elif not checkers.is_url(ROOM_URL):
                print(f"{ROOM_URL} is not a valid (room) URL!")

            elif not RTSP_STREAM_URL[0:19] == "rtsp://rtsp.stream/":
                print(f"{RTSP_STREAM_URL} is not a valid (rtsp) URL!")
                print(RTSP_STREAM_URL[0:19])

            elif YAML_FILE_NAME and YAML_FILE_NAME.endswith(".yaml"):
                with open(YAML_FILE_NAME, "w") as file:
                    dict_file = {"ROOM_URL" : ROOM_URL, "RTSP_STREAM_URL" : RTSP_STREAM_URL, "HEADLESS" : HEADLESS, "WEEKDAY" : WEEKDAY, "START" : START, "END" : END}
                    documents = yaml.dump(dict_file, file)
                    print("Writing to file!")
        elif event == "Load File":
            if YAML_FILE_NAME and YAML_FILE_NAME.endswith(".yaml") and os.path.exists(YAML_FILE_NAME):
                with open(YAML_FILE_NAME, "r") as file:
                    try:
                        yaml_contents = yaml.safe_load(file)
                        print(yaml_contents)
                        window.Element("-ROOM_URL-").update(yaml_contents["ROOM_URL"])
                        window.Element("-RTSP_STREAM_URL-").update(yaml_contents["RTSP_STREAM_URL"])
                        print(yaml_contents["HEADLESS"])
                        window.Element("-HEADLESS-").update(yaml_contents["HEADLESS"])
                        window.Element("-WEEKDAY-").update(yaml_contents["WEEKDAY"])
                        window.Element("-START-").update(yaml_contents["START"])
                        window.Element("-END-").update(yaml_contents["END"])
                        

                    except yaml.YAMLError as exc:
                        print(exc)


    window.close()