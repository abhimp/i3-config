#!/usr/bin/env bash

primary=$(xrandr --query | grep " connected" | grep primary | cut -d" "  -f1)

#without primary this script is useless
if [ "$primary" != "eDP-1" ]
then
    exit 0
fi
displays=(`xrandr --query | grep " connected" | grep -e '[[:digit:]]\+x[[:digit:]]\++[[:digit:]]\++[[:digit:]]' | cut -d\  -f1| xargs`)

if [ ${#displays[@]} -gt 1 ]
then
    xrandr --output eDP-1 --primary --mode 1920x1080 --pos 0x0 --rotate normal --output HDMI-1 --off
else
    xrandr --output eDP-1 --primary --mode 1920x1080 --pos 0x0 --rotate normal --output HDMI-1 --mode 1920x1080 --pos 1920x0 --rotate normal
fi


sleep 2
~/.config/polybar/launch.sh
