import serial
import threading
import logging
import serial.tools
import threading
from pathlib import Path

from . import bootstrap
from . import record

class Handler:
    config: str | Path
    data_dir: Path
    data_path: Path
    init_time: str
    connection: dict
    device: serial.Serial
    indices: list[int] = []

    def __init__(self, config: str = "default_config.toml", data_dir: str | None = None):

        # Store inputs
        self.config = config
        self.data_dir = data_dir

        # Initialize data directory and log file
        bootstrap.init_data_dir(self.data_dir)
        bootstrap.create_log_file()
        
    def start_recording(self, stop_event: threading.Event | None = None) -> None:
        record.record(self.indices, stop_event)