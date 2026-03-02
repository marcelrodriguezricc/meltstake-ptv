import logging
import sys
import threading

from meltstake_ptv.handler import Handler
from . import utils

log = logging.getLogger(__name__)

def setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

def _quit_listener(stop_event: threading.Event) -> None:
    """Blocks waiting for user input; sets stop_event when user requests quit."""
    while not stop_event.is_set():
        line = sys.stdin.readline()
        if not line:  # stdin closed
            return
        if line.strip().lower() in {"s", "quit", "exit", "q", "stop"}:
            stop_event.set()
            return
        
def main() -> None:
    args = utils.parse_args()
    setup_logging(args.debug)

    log.debug("Debugging enabled...")

    data_dir=f"{args.data}/ptv"

    handler = Handler(args.config, data_dir)

    user = input("Press Enter to start recording video (or type 's' then Enter to stop): ").strip().lower()
    if user in {"s", "quit", "exit", "q", "stop"}:
        return

    stop_event = threading.Event()
    t = threading.Thread(target=_quit_listener, args=(stop_event,), daemon=True)
    t.start()

    try:
        handler.start_recording(stop_event=stop_event)
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    main()