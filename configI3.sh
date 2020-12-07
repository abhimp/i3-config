#!/usr/bin/env bash

install="pacman -S"

$install xss-lock xorg-xrandr xorg-xfd brightnessctl scrot i3-gaps i3status pasystray feh rofi libpulse

pip install pikaur pyalpm i3ipc

python -m pikaur -S ts-polkitagent

ln -sf ~/.config/i3 $PWD/i3
