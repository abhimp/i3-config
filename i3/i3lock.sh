#!/bin/bash
rm /tmp/screen_locked.png /tmp/screen_locked2.png
scrot /tmp/screen_locked.png
convert /tmp/screen_locked.png -blur 4x4 /tmp/screen_locked2.png
i3lock -i /tmp/screen_locked2.png
