import logging
import sys
import threading

from meltstake_ptv.handler import Handler
from . import utils

log = logging.getLogger(__name__)

# Sets up debug tool to print log entries to console
def setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

# Listener function for start stop of capture from CLI
def _quit_listener(stop_event: threading.Event) -> None:
    """Blocks waiting for user input; sets stop_event when user requests quit."""
    while not stop_event.is_set():
        line = sys.stdin.readline()
        if not line:
            return
        if line.strip().lower() in {"s", "quit", "exit", "q", "stop"}:
            stop_event.set()
            return

# Main loop (runs when package is executed)
def main() -> None:

    # Parse arguments from CLI execution
    args = utils.parse_args()

    # Instantiate debug argument in variable
    debug = args.debug

    # Get data directory from arguments
    data_dir=f"{args.data}/ptv"

    # Initialize handler object, pass configuration name and data directory path
    handler = Handler(args.config, data_dir)

    # If debugging is enabled...
    if debug:

        # Setup logging
        setup_logging(debug)
        log.debug("Debugging enabled...")

        # Print instructions for listener
        user = input("Press Enter to start recording video (or type 's' then Enter to stop): ").strip().lower()
        if user in {"s", "quit", "exit", "q", "stop"}:
            return

        # Start thread for listener
        stop_event = threading.Event()
        t = threading.Thread(target=_quit_listener, args=(stop_event,), daemon=True)
        t.start()

        # Tell handler to start recording
        try:
            handler.start_recording(stop_event=stop_event)
        except KeyboardInterrupt:
            stop_event.set()

    # If debugging is not enabled...
    else:
        
        # Record without listening for loop break
        stop_event = None
        handler.start_recording(stop_event=stop_event)

if __name__ == "__main__":
    main()