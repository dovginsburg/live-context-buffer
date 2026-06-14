import requests
headers = {
    "Authorization": "Bearer ff608c97-432c-4cce-947c-857ae54d5cdb",
    "Content-Type": "application/json"
}
try:
    r = requests.get("https://api.rachio.com/1/public/person/info", headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    print(r.json())
except Exception as e:
    print(f"Error: {e}")
