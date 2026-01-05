import requests

url = "http://127.0.0.1:8000/api/login"
data = {"username": "admin", "password": "123"}

try:
    print(f"Attempting login at {url}...")
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Connection Error: {e}")
