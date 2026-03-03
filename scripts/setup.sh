#!/usr/bin/env bash

# Install git, ffmpeg
sudo apt update
sudo apt install git -y
sudo apt install ffmpeg -y
sudo apt install v4l-utils -y

# Create virtual machine
python3 -m venv /home/$USER/meltstake-ptv/.venv

# Install requirements
pip install -r requirements.txt

# Install this package
python -m pip install -e .
