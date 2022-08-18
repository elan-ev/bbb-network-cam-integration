#!/bin/bash

#set -x #for debugging

#example rtsp stream from https://www.wowza.com/developer/rtsp-stream-test
RTSP_STREAM="rtsp://rtsp.stream/pattern"
# RTSP_STREAM="rtsp://camera-42-209.virtuos.uos.de/mediainput/h264/stream_1"

ROOM_URL="https://bbb.elan-ev.de/b/art-gli-xx9-d2d"
HEADLESS="false"

#declare properties for created virtual camera
VC_VIDEO_DEVICE_NR=10
VC_VIDEO_DEVICE="/dev/video$VC_VIDEO_DEVICE_NR"
VC_CAMERA_NAME="Virtual Camera"


#always remove v4l2loopback module from kernel before initializing it again
sudo modprobe -r v4l2loopback
sudo modprobe v4l2loopback video_nr=$VC_VIDEO_DEVICE_NR card_label="$VC_CAMERA_NAME" exclusive_caps=1
sleep 1


#stream input into virtual camera (executed in background to allow for execution of the rest of the script)
ffmpeg -i $RTSP_STREAM -f v4l2 -vcodec rawvideo -pix_fmt yuv420p $VC_VIDEO_DEVICE &

#get pid of ffmpeg command to kill it afterwards
pid1="$!"


#wait until the Virtual Camera has an imput image (i.e., does not have image size 0)
while [ $(v4l2-ctl --device=$VC_VIDEO_DEVICE --all | grep "Size Image" | head -1 |awk '{print $4}') -eq "0" ]
do
    echo "Waiting for camera stream..."
    sleep 1
done


#get script directory and execute python script for connecting to the meeting
SCRIPT_DIR="$(dirname "$0")"
python3 $SCRIPT_DIR/cam_integration.py $ROOM_URL $HEADLESS "$VC_CAMERA_NAME"


#kill ffmpeg 
sudo kill -15 $pid1
sleep 1
exit 0
