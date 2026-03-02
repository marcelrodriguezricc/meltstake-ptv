from __future__ import annotations
import cv2
from pathlib import Path
import threading

def set_data_path(data_path):
    """Set global data path variable for "record" module."""

    global _DATA_PATH
    _DATA_PATH = data_path

def record(indices: list[int], stop_event: threading.Event | None = None):
    return None