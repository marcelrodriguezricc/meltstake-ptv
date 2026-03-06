#!/usr/bin/env bash
set -euo pipefail

# Install git, ffmpeg
sudo apt update
sudo apt install git -y
sudo apt install ffmpeg -y
sudo apt install v4l-utils -y

# Update the package list
apt-get update

# Install Python tooling for venvs
apt-get install -y python3 python3-venv python3-pip

# Create virtual environment
python3 -m venv /home/$USER/meltstake-ptv/.venv

# Install requirements (using venv's pip directly)
/home/$USER/meltstake-ptv/.venv/bin/pip install -r requirements.txt

# Install this package (using venv's pip directly)
/home/$USER/meltstake-ptv/.venv/bin/pip install -e .
