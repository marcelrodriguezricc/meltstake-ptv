#!/usr/bin/env bash
set -euo pipefail

# Set repo path
REPO="/home/$SUDO_USER/meltstake-ptv"

# Install ffmpeg, v4l-utils
sudo apt update
sudo apt install ffmpeg -y
sudo apt install v4l-utils -y

# Install Python tooling for venvs
sudo apt-get install -y python3 python3-venv python3-pip

# Create virtual environment
python3 -m venv "$REPO/venv"

# Install requirements
"$REPO/venv/bin/pip" install -r "$REPO/requirements.txt"

# Install this package
"$REPO/venv/bin/pip" install -e "$REPO"