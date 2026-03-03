import threading
from pathlib import Path

from . import bootstrap
from . import record

class Handler:
    config: str | Path
    data_dir: Path
    camera_ctl: dict
    devices: list[str]

    # Runs on object initialization
    def __init__(self, config: str = "default_config.toml", data_dir: str | None = None):

        # Store inputs
        self.config = config
        self.data_dir = data_dir

        # Initialize data directory and log file
        bootstrap.init_data_dir(self.data_dir)
        bootstrap.create_log_file()

        # From configuration file - populate camera control setting dictionary
        self.camera_ctl = bootstrap.parse_config(self.config)

        # Compile a list of all connected video devices
        self.devices = bootstrap.detect_devices(self.camera_ctl)

    # Begins capture
    def start_recording(self, stop_event: threading.Event | None = None) -> None:
        record.record(self.devices, self.camera_ctl, stop_event)