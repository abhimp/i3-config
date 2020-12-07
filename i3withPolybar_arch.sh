#!/usr/bin/env bash

bash configI3.sh

python -m pip install pydbus pikaur

sudo pacman --color=always --overwrite "*" --sync --asdeps python-sphinx cmake jsoncpp libmpdclient
python -m pikaur -S polybar
python -m pikaur -S ttf-unifont siji-git xorg-fonts-misc

ln -sf ~/.config/polybar $PWD/polybar

