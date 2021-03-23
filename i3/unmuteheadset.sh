#!/usr/bin/env bash
pactl set-sink-port alsa_output.pci-0000_00_1b.0.analog-stereo analog-output-headphones
pactl set-source-port alsa_input.pci-0000_00_1b.0.analog-stereo analog-input-headset-mic

