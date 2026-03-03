import threading
import subprocess
import time
import re
import select
import sys
import json
from pathlib import Path

from . import utils

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

    ctrl_pairs = []

    for key, value in camera_ctl.items():
        if key in V4L2_MAP:
            v4l_name = V4L2_MAP[key]
            ctrl_pairs.append(f"{v4l_name}={value}")

    if not ctrl_pairs:
        utils.append_log(f"Failed to map configuration parameter names to V4L2 argument names, please check configuration file for errors or use default_config")
        return

    ctrl_string = ",".join(ctrl_pairs)
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

    if proc.stderr is None:
        utils.append_log("Monitor thread: stderr pipe is None.")
        return

    fps_pattern = re.compile(r"fps=\s*([\d\.]+)")
    drop_pattern = re.compile(r"drop=\s*(\d+)")
    dup_pattern = re.compile(r"dup=\s*(\d+)")

    last_drop = 0
    
    start = time.time()

    for line in proc.stderr:
        # FPS check
        fps_match = fps_pattern.search(line)
        if fps_match and time.time() - start > 2.0:
            current_fps = float(fps_match.group(1))
            if current_fps < expected_fps * 0.95:
                utils.append_log(f"FPS DROP: {current_fps:.2f}")

        # Drop check
        drop_match = drop_pattern.search(line)
        if drop_match:
            current_drop = int(drop_match.group(1))
            if current_drop > last_drop:
                dropped_now = current_drop - last_drop
                utils.append_log(f"FRAMES DROPPED: +{dropped_now} (total={current_drop})")
                last_drop = current_drop

        # Duplicate check
        dup_match = dup_pattern.search(line)
        if dup_match:
            dup_count = int(dup_match.group(1))
            if dup_count > 0:
                utils.append_log(f"DUPLICATED FRAMES: {dup_count}")

def _report_file_stats(out_file: Path) -> None:
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

        data = json.loads(result.stdout)
        stream = data["streams"][0]

        frames = int(stream.get("nb_read_frames", 0))
        duration = float(stream.get("duration", 0))
        avg_rate = stream.get("avg_frame_rate", "0/0")

        # Convert avg_frame_rate (e.g. "60/1") to float
        num, den = avg_rate.split("/")
        actual_fps = float(num) / float(den) if float(den) != 0 else 0.0

        utils.append_log(
            f"FINAL STATS: {out_file.name} | "
            f"frames={frames} | duration={duration:.2f}s | "
            f"avg_fps={actual_fps:.2f}"
        )

    except Exception as e:
        utils.append_log(f"Failed to extract stats for {out_file}: {e}")

def set_data_path(data_path):
    """Set global data path variable for "record" module."""

    global _DATA_PATH
    _DATA_PATH = data_path

def device_record(device: str, camera_ctl: dict) -> subprocess.Popen:

    _apply_config(device, camera_ctl)

    fps = camera_ctl["fps"]
    res_x = camera_ctl["res_x"]
    res_y = camera_ctl["res_y"]
    format_val = camera_ctl["format"]

    format_str = "mjpeg" if format_val == 0 else "yuyv422"

    if format_val == 0:
        format_str = "mjpeg"
        ext = ".mkv"
        vcodec = "copy"
    else:
        format_str = "yuyv422"
        ext = ".mkv"
        vcodec = "libx264"

    data_path = Path(_DATA_PATH)
    dev_name = Path(device).name
    out_file = data_path / f"{dev_name}{ext}"
    out_file.parent.mkdir(parents=True, exist_ok=True)

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

    return subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)

def record(devices: list[str], camera_ctl: dict, stop_event: threading.Event | None = None) -> None:
    procs = [device_record(device, camera_ctl) for device in devices]

    # Start one monitor thread per process
    monitors: list[threading.Thread] = []
    expected_fps = int(camera_ctl["fps"])

    utils.append_log(f"Starting recording for devices: {devices}")

    for device, proc in zip(devices, procs):
        t = threading.Thread(
            target=_monitor_fps,
            args=(proc, expected_fps),
            daemon=True,
            name=f"ffmpeg-monitor-{device}",
        )
        t.start()
        monitors.append(t)
    
    start_t = time.monotonic()
    next_heartbeat = start_t + 10.0

    try:
        while True:
            if stop_event is not None and stop_event.is_set():
                break

            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                user_input = sys.stdin.readline().strip()
                if user_input.lower() in ("q", "quit", "exit", "stop"):
                    utils.append_log("Stop command received from CLI.")
                    break

            now = time.monotonic()
            if now >= next_heartbeat:
                elapsed = now - start_t
                utils.append_log(
                    f"Capture heartbeat: running for {elapsed:.1f}s ({elapsed/60.0:.1f} min)"
                )
                next_heartbeat += 10.0

            for device, p in zip(devices, procs):
                if p.poll() is not None:
                    utils.append_log(
                        f"FFmpeg exited unexpectedly for {device} (code={p.returncode})."
                    )
                    return

            time.sleep(0.2)

    except KeyboardInterrupt:
        utils.append_log("Stop requested; ending deployment.")

    finally:
        for p in procs:
            p.terminate()

        for p in procs:
            p.wait()
            dev_name = Path(device).name
            ext = ".mkv"
            out_file = Path(_DATA_PATH) / f"{dev_name}{ext}"

            _report_file_stats(out_file)
        utils.append_log("All capture processes stopped.")