from datetime import datetime

from constants.logLock import log_buffer, log_lock
from utils.formatLogLine import format_log_line


def get_current_logs():
    """Get the current logs from the buffer with Docker-style formatting"""
    with log_lock:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"<div class='log-line'><span class='log-timestamp'>{timestamp}</span><span class='log-info'>Log Viewer - Last {len(log_buffer)} lines</span></div>\n"

        # Return log buffer with Docker-style formatting
        if log_buffer:
            formatted_logs = []
            prev_line = None
            for line in log_buffer:
                if line != prev_line:  # Avoid duplicate consecutive lines
                    # Format the log line with timestamp and color coding
                    formatted_line = format_log_line(line)
                    formatted_logs.append(formatted_line)
                prev_line = line
            return header + "\n".join(formatted_logs)
        else:
            return (
                header
                + "<div class='log-line'><span class='log-info'>No logs yet.</span></div>"
            )
