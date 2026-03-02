from pathlib import Path
import time
import argparse
import logging

log = logging.getLogger(__name__)
_DATA_PATH = None

def _utc_time_part() -> str:
    """Return the current UTC time as HH:MM:SS."""

    # Get UTC time in human-readable format (hours.minutes.seconds)
    my_time = time.strftime("%H:%M:%S", time.gmtime())

    return my_time

def set_data_path(data_path):
    """Set global data path variable for "utils" module."""
    global _DATA_PATH
    _DATA_PATH = data_path

def append_log(line: str) -> None:
    """Append a line to the log file with a UTC time prefix.

    Args:
        line: Message to append (a trailing newline is added automatically).
    """

    # Get path to data directory from global variable (set during initialization)
    data_path = _DATA_PATH
    
    # UTC time to prepend each log entry
    prefix = _utc_time_part()

    # If debug mode enabled, print all logged lines to console
    log.debug(line)

    log_path = Path(f"{data_path}/ptv.log")

    # Open file and append line
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"{prefix}: {line.rstrip()}\n")

def make_file(filename: str) -> Path:
    """Create a path under `dir`, creating the directory if needed.

    Args:
        filename: Name of file with suffix
    """

    # Prepend user home directory
    out_dir = Path(_DATA_PATH).expanduser()

    # Make directory if it doesn't already exist
    out_dir.mkdir(parents=True, exist_ok=True)

    # Set file path with directory/filename
    out_path = out_dir / filename

    # Create file
    out_path.touch(exist_ok=True)

    return out_path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for running a Melt Stake 881A sonar deployment.
    """

    p = argparse.ArgumentParser(description="Melt Stake 881A Sonar deployment runner")

    # Default configuration file
    default_config = "default_config.toml"

    # Get repository root
    ROOT = Path(__file__).resolve().parents[2]
    default_data_dir = ROOT / "data"

    # Debugging mode, prints log entries to console
    p.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    # Path to TOML configuration file
    p.add_argument(
        "-c",
        "--config",
        default=default_config,
        help="Path to TOML config (default: default_config.toml)",
    )

    # Path to TOML configuration file
    p.add_argument(
        "-d",
        "--data",
        "--data-path",
        "--data-dir",
        default=default_data_dir,
        help="Path where data, logs, and other files created at runtime will be stored (default: ROOT/data)",
    )

    return p.parse_args()