#!/bin/bash

#set -x #for debugging

#example rtsp stream from https://www.wowza.com/developer/rtsp-stream-test
RTSP_STREAM="rtsp://rtsp.stream/pattern"
# RTSP_STREAM="rtsp://131.173.172.32/mediainput/h264/stream_1"

ROOM_URL="https://bbb.elan-ev.de/b/art-gli-xx9-d2d"
HEADLESS="true"
VC_CAMERA_NAME="Virtual_Camera"

MIC_NAME="Virtual_Microphone"

#get script directory and execute python script for connecting to the meeting
SCRIPT_DIR="$(dirname "$0")"
python3 $SCRIPT_DIR/cam_integration.py $ROOM_URL $HEADLESS $VC_CAMERA_NAME  $RTSP_STREAM $MIC_NAME
