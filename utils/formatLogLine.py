import html
import re
from datetime import datetime


def format_log_line(line, ws=False):
    """Format a log line to match Docker container log style"""
    # Extract timestamp if present, or generate one
    timestamp_match = re.search(r"^\[([\d\-\s:]+)\]", line)
    if timestamp_match:
        timestamp = timestamp_match.group(1)
        content = line[len(timestamp_match.group(0)) :].strip()
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        content = line

    # Determine log level based on content
    css_class = "log-info"
    if re.search(r"error|exception|fail|critical", content, re.IGNORECASE):
        css_class = "log-error"
    elif re.search(r"warn|caution", content, re.IGNORECASE):
        css_class = "log-warning"

    # Format the line with HTML
    if ws:
        return f"<span class='log-timestamp'>{timestamp}</span><span class='{css_class}'>{html.escape(content)}</span>"

    return f"<div class='log-line'><span class='log-timestamp'>{timestamp}</span><span class='{css_class}'>{html.escape(content)}</span></div>"
