import requests
import time
# from requests.auth import HTTPBasicAuth

# Your EC2 instance's FastAPI URL
url = 'http://13.201.91.59:8000/count'

# Example base64 image string
base64_image = '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'

# Define the payload to be sent in the POST request
data = {"base64_image": base64_image}

# Authentication credentials
username = 'user@example.com'
password = 'string'

# Replace 'your_token_here' with the actual token you receive after authentication
headers = {
    "Authorization": "Bearer your_token_here"
}

def make_requests(n):
    times = []
    for i in range(n):
        start = time.time()
        response = requests.post(url, json=data, headers= headers)
        end = time.time()
        times.append(end - start)
        print(f'Request {i+1}: {response.status_code}, Time: {end - start:.4f} seconds')
        if response.status_code != 200:
            print(f'Failed Request {i+1}: {response.text}')
    avg_time = sum(times) / len(times)
    print(f'Average time for {n} requests: {avg_time:.4f} seconds')
# Make 1, 10, and 50 requests to the '/count' endpoint
# make_requests(1)
# make_requests(10)
make_requests(1)
