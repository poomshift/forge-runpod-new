import concurrent.futures
import threading

# log buffer aka. like queue first in first out and threding lock to prevent race condition.
log_buffer = []
log_lock = threading.Lock()

# idk why have this
thread_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
