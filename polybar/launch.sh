#!/usr/bin/env bash

# #!/bin/bash
#
# # Terminate already running bar instances
# killall -q polybar
#
# # Wait until the processes have been shut down
# while pgrep -u $UID -x polybar >/dev/null; do sleep 1; done
#
# # Launch Polybar, using default config location ~/.config/polybar/config
# polybar mybar &
#
# echo "Polybar launched..."

#
# Terminate already running bar instances
killall -q polybar
# If all your bars have ipc enabled, you can also use
# polybar-msg cmd quit
#
# Launch bar1 and bar2
export DISPLAY=:0
echo "---" | tee -a /tmp/polybar1.log /tmp/polybar2.log
# polybar base >>/tmp/polybar1.log 2>&1 & disown

primary=$(xrandr --query | grep " connected" | grep primary | cut -d" "  -f1)

if [ "$primary" == "" ]
then
    primary=$(xrandr --query | grep " connected" | head -1| cut -d" "  -f1)
fi

for m in $(xrandr --query | grep " connected" | cut -d" " -f1)
do
    if [ "$primary" == "" ]
    then
        MONITOR=$m polybar full >>/tmp/polybar1.log 2>&1 & disown
    else
        if [ "$m" == "$primary" ]
        then
            TRAY_POS=right MONITOR=$m polybar full >>/tmp/polybar1.log 2>&1 & disown
        else
            TRAY_POS=none MONITOR=$m polybar full >>/tmp/polybar1.log 2>&1 & disown
        fi
    fi
done
# polybar full  & disown
# polybar space  & disown
# sleep 1
# polybar date  & disown
# sleep 1
# polybar right  & disown
#
echo "Bars launched..."

ps -ef | grep $PPID > /tmp/ppop
