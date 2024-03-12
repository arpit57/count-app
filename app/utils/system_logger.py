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
    command = "ps -eo pcpu | awk 'NR>1 {sum += $1} END {print sum}'"
    result = subprocess.run(command, capture_output=True, shell=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip() + '%'
    else:
        return "Error obtaining CPU usage"

def trim_logs():
    """Keep only the latest 500 log entries."""
    with lock:
        try:
            with open(LOGS_FILE, 'r+') as file:
                lines = file.readlines()
                if len(lines) > 500:
                    file.seek(0)
                    file.truncate()
                    # Keep only the last 500 entries
                    file.writelines(lines[-500:])
        except FileNotFoundError:
            pass  # If the file doesn't exist yet, there's nothing to trim

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

        # Log the current request
        with lock, open(LOGS_FILE, 'a') as log_file:
            log_file.write(json.dumps(log_entry) + '\n')

        # Reset request counter (if desired)
        # This line resets the counter after each logged request,
        # if you want to maintain a continuous count, you should move this outside
        with lock:
            request_counter = 0
        
        # Trim the log file to keep only the latest 500 entries
        trim_logs()

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
