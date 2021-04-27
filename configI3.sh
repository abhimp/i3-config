#!/usr/bin/env bash

install="sudo pacman -S"

$install xss-lock xorg-xrandr xorg-xfd brightnessctl scrot i3-gaps i3status pasystray feh rofi libpulse gnome-keyring i3lock imagemagick

pip install pikaur pyalpm i3ipc

python -m pikaur -S ts-polkitagent

ln -sf $PWD/i3 ~/.config/i3
