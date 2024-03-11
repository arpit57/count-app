import subprocess
import datetime
import json
import os
from threading import Lock
import traceback

LOGS_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_FILE = os.path.join(LOGS_DIR, 'logs.txt')
lock = Lock()

# Keep track of the number of requests
request_counter = 0

def get_cpu_usage():
    # Use `ps` to aggregate CPU usage across all processes
    command = "ps -eo pcpu | awk 'NR>1 {sum += $1} END {print sum}'"
    result = subprocess.run(command, capture_output=True, shell=True, text=True)
    if result.returncode == 0:
        # Returns total CPU usage percentage
        return result.stdout.strip() + '%'
    else:
        return "Error obtaining CPU usage"

def log_request_stats(request_type, endpoint):
    try:
        global request_counter
        timestamp = datetime.datetime.now().isoformat()
        cpu_usage = get_cpu_usage()
        
        with lock:
            request_counter += 1
            current_request_count = request_counter

        log_entry = {
            'timestamp': timestamp,
            'request_type': request_type,
            'endpoint': endpoint,
            'CPU_usage': cpu_usage,
            'simultaneous_requests': current_request_count
        }

        with lock, open(LOGS_FILE, 'a') as log_file:
            log_file.write(json.dumps(log_entry) + '\n')

        with lock:
            request_counter = 0  # Consider moving this outside the try block if continuous counting without resetting is desired.
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

# Example usage from within your FastAPI application
# log_request_stats('GET', '/api/some-endpoint')
