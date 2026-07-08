import tomllib
import sys
import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path

from . import utils
from . import record

_DATA_PATH = None

_DEFAULT_CAMERA_CTL: dict[str, int] = {
    "auto_exposure": 1,
    "exposure_time": 157,
    "dynamic_fr": 0,
    "bright": 0,
    "contrast": 42,
    "saturation": 64,
    "hue": 0,
    "auto_wb": 0,
    "gamma": 100,
    "gain": 0,
    "pl_freq": 2,
    "wb_temp": 6200,
    "sharp": 0,
    "bl_comp": 20,
    "fps": 60,
    "format": "mjpeg",
    "res_x": 1600,
    "res_y": 1200,
    "segment_seconds": 300,
}

def _coerce_int(val: object) -> int | None:
    """If input is not an integer, trys to set it to be an integer, if not returns None."""

    # If entry is a boolean, return none
    if isinstance(val, bool):
        return None
    
    # If entry is an integer, return normally
    if isinstance(val, int):
        return val
    
    # If entry is a float, convert to integer
    if isinstance(val, float) and val.is_integer():
        return int(val)
    
    # If entry is a string, convert to integer, if blank return none
    if isinstance(val, str):
        s = val.strip()
        if s == "":
            return None
        try:
            return int(s, 10)
        except ValueError:
            return None
        
    return None

def _set_default(dst: dict, key: str, default: object, why: str) -> None:
    """Sets input key to default value."""

    utils.append_log(f"Config '{key}' invalid ({why}); using default {default!r}")

    # Set input key to default
    dst[key] = default

def _clamp_int(dst: dict, key: str, default: int, lo: int, hi: int,) -> None:
    """Checks whether integer is in range of possible values; forces it to minimum if below, maximum if above, and default if input is not an integer."""

    # Get number from key
    raw = dst.get(key, None)

    # Set to integer
    n = _coerce_int(raw)

    # If None is returned, set to default
    if n is None:
        _set_default(dst, key, default, f"not an int: {raw!r}")
        return
    
    # If integer is below minimum, set to minimum
    if n < lo:
        n = lo
        return
    
    # If integer is above maximum, set to maximum
    if n > hi:
        n = hi
        return
    
    # Set input key
    dst[key] = n

def _enum_int(dst: dict, key: str, default: int, allowed: set[int],) -> None:
    """"Checks whether input integer matches allowed values."""
    
    # Get key
    raw = dst.get(key, None)

    # If it's not an integer, change it to type integer, returns None if not possible
    n = _coerce_int(raw)

    # If the input cannot be coerced or allowed, set to default
    if n is None or n not in allowed:
        _set_default(dst, key, default, f"must be one of {sorted(allowed)}; got {raw!r}")
        return
    
    # Set input key
    dst[key] = n

def _load_config(config: str) -> dict:
    """Load configuration file from ROOT/configs directory.

    Falls back to default_config.toml if the requested config can't be loaded.
    """

    # Establish configuration path
    ROOT = Path(__file__).resolve().parents[2]
    configs_dir = ROOT / "configs"
    primary_path = configs_dir / Path(config)
    fallback_path = configs_dir / "default_config.toml"

    # Function to load configuration .toml file at given path as a dictionary
    def _try_load(path: Path) -> dict:
        with path.open("rb") as f:
            return tomllib.load(f)

    # Try requested config
    try:
        cfg = _try_load(primary_path)

    # If it fails, fallback to default_config.toml
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError) as e1:
        utils.append_log(f"Failed to load configuration file at {primary_path}: {e1}")

        # If primary already is the fallback, don't loop
        if primary_path.resolve() == fallback_path.resolve():
            raise

        utils.append_log(f"Falling back to default configuration at {fallback_path}")

        # Try default_config.toml
        try:
            cfg = _try_load(fallback_path)
        except (FileNotFoundError, tomllib.TOMLDecodeError, OSError) as e2:
            utils.append_log(f"Failed to load fallback configuration at {fallback_path}: {e2}")
            raise RuntimeError(
                f"Failed to load config {primary_path} and fallback {fallback_path}"
            ) from e2
        else:
            utils.append_log(f"Fallback configuration file loaded: {fallback_path}")
            return cfg
    else:
        utils.append_log(f"Configuration file loaded: {primary_path}")
        return cfg
    
def parse_config(config: str) -> tuple[dict, dict]:
    """Parse configuration .toml file and return connection + switch parameters as dicts."""

    # Load configuration from .toml file
    cfg = _load_config(config)

    # Try to get camera_ctl key, if it fails, set to default
    try:
        camera_ctl = dict(cfg.get("camera_ctl", {}))
    except Exception as e:
        utils.append_log(f"Failed to parse configuration from config.toml: {e}, setting to default.")
        camera_ctl = _DEFAULT_CAMERA_CTL
        raise
    
    # Fill missing camera control keys with defaults
    for k, v in _DEFAULT_CAMERA_CTL.items():
        camera_ctl.setdefault(k, v)

    # Validate camera control parameters
    _enum_int(camera_ctl, "auto_exposure", _DEFAULT_CAMERA_CTL["auto_exposure"], {0, 1, 2, 3})
    _clamp_int(camera_ctl, "exposure_time", _DEFAULT_CAMERA_CTL["exposure_time"], 1, 5000)
    _enum_int(camera_ctl, "dynamic_fr", _DEFAULT_CAMERA_CTL["dynamic_fr"], {0, 1})
    _clamp_int(camera_ctl, "bright", _DEFAULT_CAMERA_CTL["bright"], -64, 64)
    _clamp_int(camera_ctl, "contrast", _DEFAULT_CAMERA_CTL["contrast"], 0, 42)
    _clamp_int(camera_ctl, "saturation", _DEFAULT_CAMERA_CTL["saturation"], 0, 42)
    _clamp_int(camera_ctl, "hue", _DEFAULT_CAMERA_CTL["hue"], -40, 40)
    _enum_int(camera_ctl, "auto_wb", _DEFAULT_CAMERA_CTL["auto_wb"], {0, 1})
    _clamp_int(camera_ctl, "gamma", _DEFAULT_CAMERA_CTL["gamma"], 72, 500)
    _clamp_int(camera_ctl, "gain", _DEFAULT_CAMERA_CTL["gain"], 0, 100)
    _enum_int(camera_ctl, "pl_freq", _DEFAULT_CAMERA_CTL["pl_freq"], {0, 1, 2})
    _clamp_int(camera_ctl, "wb_temp", _DEFAULT_CAMERA_CTL["gain"], 2800, 6500)
    _clamp_int(camera_ctl, "sharp", _DEFAULT_CAMERA_CTL["sharp"], 0, 6)
    _clamp_int(camera_ctl, "bl_comp", _DEFAULT_CAMERA_CTL["bl_comp"], 0, 20)
    _clamp_int(camera_ctl, "fps", _DEFAULT_CAMERA_CTL["fps"], 0, 60)
    _clamp_int(camera_ctl, "format", _DEFAULT_CAMERA_CTL["format"], 0, 1)
    _clamp_int(camera_ctl, "res_x", _DEFAULT_CAMERA_CTL["res_x"], 0, 1600)
    _clamp_int(camera_ctl, "res_y", _DEFAULT_CAMERA_CTL["res_y"], 0, 1200)
    _clamp_int(camera_ctl, "segment_seconds", _DEFAULT_CAMERA_CTL["segment_seconds"], 1, 86400)

    utils.append_log(f"Configuration file parsed - {camera_ctl}")

    return camera_ctl

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

def detect_devices(camera_ctl: dict) -> list[str]:
    """Detect stellarHD video devices that support requested format."""

    # Get format from configuration
    fmt = camera_ctl["format"]

    # Map menu integers to strings
    required_format = "MJPG" if fmt == 0 else "YUYV"

    # Initialize array for storage of device path strings
    devices: list[str] = []

    try:

        # List devices using V4L2
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            capture_output=True,
            text=True,
            timeout=2
        )

        # Split results into separate by blank line
        blocks = result.stdout.split("\n\n")

        # For each device...
        for block in blocks:

            # If "stellarHD" is present...
            if "stellarHD" in block:
                matches = re.findall(r"/dev/video\d+", block)

                for dev in matches:

                    fmt_result = subprocess.run(
                        ["v4l2-ctl", "--device", dev, "--list-formats-ext"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )

                    if required_format in fmt_result.stdout:
                        devices.append(dev)

    except Exception as e:
        utils.append_log(f"Runtime error while using V4L2 to find stellarHD devices: {e}")
        raise

    if not devices:
        utils.append_log(f"V4L2 did not find stellarHD devices, exiting program.")
        sys.exit(1)
    
    devices.sort(key=lambda x: int(x.replace("/dev/video", "")))

    utils.append_log(
        f"Found stellarHD devices supporting {required_format}: {devices}"
    )

    return devices