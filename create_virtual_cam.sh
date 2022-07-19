#!/bin/sh

set -x #for debugging

#declare device number and device name for input camera
VIDEO_DEVICE_NR=0
ORIGINAL_VIDEO_DEVICE="/dev/video$VIDEO_DEVICE_NR"

#declare properties for created virtual camera
VC_VIDEO_DEVICE_NR=10
VC_VIDEO_DEVICE="/dev/video$VC_VIDEO_DEVICE_NR"
VC_CAMERA_NAME="\"Virtual Camera\""

#if virtual camera does not exist yet, create it
if [ ! -c $VC_VIDEO_DEVICE ]; then
	sudo modprobe v4l2loopback video_nr=$VC_VIDEO_DEVICE_NR card_label=$VC_CAMERA_NAME exclusive_caps=1
fi

#stream input into virtual camera
ffmpeg -i $ORIGINAL_VIDEO_DEVICE -f v4l2 -vcodec rawvideo -pix_fmt yuv420p $VC_VIDEO_DEVICE