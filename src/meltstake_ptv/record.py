import threading
import subprocess
import time
import re
import json
from pathlib import Path

from . import utils

# Mapping of configuration keys to V4L2 keys
V4L2_MAP = {
    "auto_exposure": "auto_exposure",
    "exposure_time": "exposure_time_absolute",
    "dynamic_fr": "exposure_dynamic_framerate",
    "bright": "brightness",
    "contrast": "contrast",
    "saturation": "saturation",
    "hue": "hue",
    "auto_wb": "white_balance_automatic",
    "gamma": "gamma",
    "gain": "gain",
    "pl_freq": "power_line_frequency",
    "wb_temp": "white_balance_temperature",
    "sharp": "sharpness",
    "bl_comp": "backlight_compensation",
}

def _apply_config(device: str, camera_ctl: dict[str, int]) -> None:
    """Applies configuration settings to V4L2"""

    # Initialize control key-value pair array
    ctrl_pairs = []

    # For each pair in the configuration dictionary...
    for key, value in camera_ctl.items():

        # Compile a new array with the V4L2 keys and configuration values
        if key in V4L2_MAP:
            v4l_name = V4L2_MAP[key]
            ctrl_pairs.append(f"{v4l_name}={value}")

    # If there's nothing in the array...
    if not ctrl_pairs:
        utils.append_log(f"Failed to map configuration parameter names to V4L2 argument names, please check configuration file for errors or use default_config")
        return

    # Append a comma at the end of each key-value pair string
    ctrl_string = ",".join(ctrl_pairs)

    # Set the control parameters
    try:
        subprocess.run(
            ["v4l2-ctl", "-d", device, "--set-ctrl", ctrl_string],
            check=True
        )
    except Exception as e:
        utils.append_log(f"Failed to apply configuration to {device}: {e}")
        raise
    else:
        utils.append_log(f"Successfully applied configuration to {device}")

def _monitor_fps(proc: subprocess.Popen, expected_fps: int):
    """Monitor for latency events — frame rate hit / dropped frames / duplicate frames — during capture"""

    # If FFMPEG subprocess was not set up correctly for error monitoring...
    if proc.stderr is None:
        utils.append_log("Standard error (stderr) pipe is None, process was not correctly set up for error monitoring.")
        return

    # Extract numbers from FFMPEG subprocess lines
    fps_pattern = re.compile(r"fps=\s*([\d\.]+)")
    drop_pattern = re.compile(r"drop=\s*(\d+)")
    dup_pattern = re.compile(r"dup=\s*(\d+)")

    # Reset drop count
    last_drop = 0
    
    # Get time
    start = time.time()

    # Check continuous error report from FFMPEG for the following...
    for line in proc.stderr:

        # Get FPS
        fps_match = fps_pattern.search(line)

        # If FPS was retrieved 2.0 seconds have elapsed from capture initialization (FFMPEG reports 0.0 FPS on initialization)...
        if fps_match and time.time() - start > 2.0:

            # Set current FPS from error report
            current_fps = float(fps_match.group(1))

            # If the current FPS is less than 95% of expected FPS, append to log
            if current_fps < expected_fps * 0.95:
                utils.append_log(f"FPS DROP: {current_fps:.2f}")

        # Get drop events
        drop_match = drop_pattern.search(line)

        # If drop event value is found in error report...
        if drop_match:

            # Set the current drop number from error report
            current_drop = int(drop_match.group(1))

            # If the drop number is greater than previously
            if current_drop > last_drop:

                # Report the difference in dropped frames
                dropped_now = current_drop - last_drop

                # Append to log
                utils.append_log(f"FRAMES DROPPED: +{dropped_now} (total={current_drop})")

                # Set last drop with new total for future loops
                last_drop = current_drop

        # Get number of duplicate frames from error report
        dup_match = dup_pattern.search(line)

        # If duplicate frames value is found in error report...
        if dup_match:

            # Set the duplicate count from error report
            dup_count = int(dup_match.group(1))

            # If error report lists duplicated frames, append to log
            if dup_count > 0:
                utils.append_log(f"DUPLICATED FRAMES: {dup_count}")

def _report_file_stats(out_file: Path) -> None:
    """Get video file statistics with FFProbe and append to log"""

    # Try to use FFProbe to get video file statistics
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-count_frames",
                "-show_entries",
                "stream=nb_read_frames,avg_frame_rate,duration",
                "-of", "json",
                str(out_file),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse json string to dict
        data = json.loads(result.stdout)

        # Get frames, duration, and average rate values from streams key
        stream = data["streams"][0]
        frames = int(stream.get("nb_read_frames", 0))
        duration = float(stream.get("duration", 0))
        avg_rate = stream.get("avg_frame_rate", "0/0")

        # Convert average rate split to actual average FPS number
        num, den = avg_rate.split("/")
        actual_fps = float(num) / float(den) if float(den) != 0 else 0.0

        # Append statistics to log
        utils.append_log(
            f"Video Output Statistics ({out_file.name}): Frames = {frames}, Duration = {duration:.2f} seconds, Average FPS = {actual_fps:.2f}"
        )

    except Exception as e:
        utils.append_log(f"Failed to extract stats for {out_file}: {e}")

def set_data_path(data_path):
    """Set global data path variable for "record" module."""

    global _DATA_PATH
    _DATA_PATH = data_path

def device_record(device: str, camera_ctl: dict) -> subprocess.Popen:
    """
    Initialize an FFmpeg capture process for a V4L2 device and begin recording to file.

    Applies device configuration, constructs an FFmpeg command based on the provided
    control parameters, and launches it as a non-blocking subprocess.

    Args:
        device (str): Path to the V4L2 device (e.g. '/dev/video0').
        camera_ctl (dict): Camera control parameters

    Returns:
        subprocess.Popen: Handle to the running FFmpeg process, with stderr piped
        and decoded as text. Pass to _monitor_fps() to monitor capture performance,
        or to _report_file_stats() after termination to log final file statistics.
    """
   
    # Apply configuration to camera device
    _apply_config(device, camera_ctl)

    # Get FPS, resolution, and format values from configuration
    fps = camera_ctl["fps"]
    res_x = camera_ctl["res_x"]
    res_y = camera_ctl["res_y"]
    format_val = camera_ctl["format"]

    # Parse menu from configuration to format each index pertains to
    format_str = "mjpeg" if format_val == 0 else "yuyv422"

    # Filename and argument formatting for desired format
    if format_val == 0:
        format_str = "mjpeg"
        ext = ".mkv"
        vcodec = "copy"
    else:
        format_str = "yuyv422"
        ext = ".mkv"
        vcodec = "libx264"

    # Set file output path
    data_path = Path(_DATA_PATH)
    dev_name = Path(device).name
    out_file = data_path / f"{dev_name}{ext}"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Compile command based on configuration parameters
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "info",
        "-stats",
        "-f", "v4l2",
        "-thread_queue_size", "64",
        "-framerate", str(fps),
        "-video_size", f"{res_x}x{res_y}",
        "-input_format", format_str,
        "-i", device,
        "-c:v", vcodec,
        str(out_file),
    ]

    # Launch and return a running FFMPEG process
    return subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)

def record(devices: list[str], camera_ctl: dict, stop_event: threading.Event | None = None) -> None:

    # Launch FFMPEG processes for each device and store in array
    procs = [device_record(device, camera_ctl) for device in devices]

    # Initialize an array to store monitoring threads for each device
    monitors: list[threading.Thread] = []

    # Get expected FPS from configuration
    expected_fps = int(camera_ctl["fps"])

    utils.append_log(f"Starting recording for devices: {devices}")

    # For each running device...
    for device, proc in zip(devices, procs):

        # Initialize an FPS monitor thread
        t = threading.Thread(
            target=_monitor_fps,
            args=(proc, expected_fps),
            daemon=True,
            name=f"ffmpeg-monitor-{device}",
        )

        # Start the thread
        t.start()

        # Append the thread to the monitors array
        monitors.append(t)
    
    # Establish a capture heartbeat every 10 seconds
    start_t = time.monotonic()
    next_heartbeat = start_t + 10.0

    try:
        # Infinite probe loop
        while True:
            
            # If CLI input triggers stop event, break loop.
            if stop_event is not None and stop_event.is_set():
                utils.append_log("Stop requested; ending deployment.")
                break

            # Check time, if time is greater than heartbeat duration, report heartbeat to log
            now = time.monotonic()
            if now >= next_heartbeat:
                elapsed = now - start_t
                utils.append_log(
                    f"Capture heartbeat: running for {elapsed:.1f}s ({elapsed/60.0:.1f} min)"
                )
                next_heartbeat += 10.0

            # For each device with a running FFMPEG process..
            for device, p in zip(devices, procs):

                # If process unexpectedly breaks, report to log
                if p.poll() is not None:
                    utils.append_log(
                        f"FFmpeg exited unexpectedly for {device} (code={p.returncode})."
                    )
                    return

            # Check every 0.2 seconds
            time.sleep(0.2)

    # Upon exit...
    finally:

        # Terminate all FFMPEG subprocesses
        for p in procs:
            p.terminate()

        # Write video file to directory
        for p in procs:
            p.wait()
            dev_name = Path(device).name
            ext = ".mkv"
            out_file = Path(_DATA_PATH) / f"{dev_name}{ext}"
            
            # Probe for video statistics
            _report_file_stats(out_file)

        utils.append_log("All capture processes stopped.")