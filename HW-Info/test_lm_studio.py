import requests

url = "http://192.168.1.21:1234/v1/models"
try:
    resp = requests.get(url, timeout=2)
    models = resp.json().get('data', [])
    print(f"LM Studio connected. Found {len(models)} models:")
    for m in models:
        print(f" - {m['id']}")
except Exception as e:
    print(f"Error: {e}")
