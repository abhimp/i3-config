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

cnt=$(ps -ef | grep `pgrep polybar` | grep defunct | wc -l)

if [ $cnt -eq 0 ]
then
    exit
fi

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
polybar full >>/tmp/polybar1.log 2>&1 & disown
# polybar full  & disown
# polybar space  & disown
# sleep 1
# polybar date  & disown
# sleep 1
# polybar right  & disown
#
echo "Bars launched..."
