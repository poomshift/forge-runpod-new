import asyncio
import os
import time

from constants.logLock import log_buffer, log_lock
from constants.websocketEventManager import sync_broadcast_to_websockets
from utils.formatLogLine import format_log_line


def tail_log_file():
    """Continuously tail the log file and update the buffer"""
    log_file = os.path.join("/", "workspace", "logs", "comfyui.log")

    if not os.path.exists(log_file):
        os.makedirs("/","workspace","logs", exist_ok=True)
        open(log_file, "a").close()

    def follow(file_path):
        """Generator function that yields new lines in a file with proper handling of file rotation/truncation"""
        with open(file_path, "r", encoding="utf-8") as file:
            current_position = 0
            while True:
                try:
                    # Check if file has been truncated
                    file_size = os.path.getsize(file_path)
                    if file_size < current_position:
                        current_position = 0  # File was truncated, start from beginning

                    # Seek to last position
                    file.seek(current_position)

                    # Read new lines
                    new_lines = file.readlines()
                    if new_lines:
                        current_position = file.tell()
                        for line in new_lines:
                            yield line
                    else:
                        # No new lines, sleep before checking again
                        time.sleep(0.1)
                except Exception as e:
                    print(f"Error following log file: {e}")
                    time.sleep(1)  # Wait a bit longer on error

    try:
        # Start the continuous tail
        prev_line = None
        for line in follow(log_file):
            stripped_line = line.strip()
            if stripped_line:  # Only process non-empty lines and not duplicates
                with log_lock:
                    log_buffer.append(stripped_line)
                    if len(log_buffer) > 500:
                        log_buffer.pop(0)

                # Emit new log line via WebSocket (thread-safe)
                sync_broadcast_to_websockets(
                    {
                        "type": "new_log_line",
                        "line": format_log_line(stripped_line, ws=True),
                    }
                )
            prev_line = stripped_line
    except Exception as e:
        print(f"Error tailing log file: {e}")
        time.sleep(5)


def tlf_worker(tail_log_file, loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tail_log_file())
