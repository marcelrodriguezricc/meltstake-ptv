import cv2
from datetime import datetime, timezone

from . import utils
from . import record

_DATA_PATH = None

def init_data_dir(data_dir: str) -> None:
    """Initialize data directory for storage of files generated during runtime."""

    # Get datetime and format for file naming
    utc_dt = datetime.now(timezone.utc)
    dt_formatted = utc_dt.strftime("%Y-%m-%d_%H.%M.%S")
    data_path = f"{data_dir}/{dt_formatted}"
 
    # Set path to data directory as global variable in all modules
    global _DATA_PATH 
    _DATA_PATH = data_path
    utils.set_data_path(data_path)
    record.set_data_path(data_path)

def create_log_file() -> None:
    """Create log file and write an init line."""

    # Create a log file at directory "logs"
    log_path = utils.make_file("ptv.log")

    utils.append_log(f"Stereo PTV System deployment log initialized")
    utils.append_log(f"Path to log: {log_path}")