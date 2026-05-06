"""Probe puppy.walmart.com to find the sharing publish API endpoint."""
import configparser, pathlib, requests, json, urllib3
urllib3.disable_warnings()

cfg = configparser.ConfigParser()
cfg.read(pathlib.Path.home() / ".code_puppy" / "puppy.cfg")
token = cfg["puppy"]["puppy_token"].strip()
print(f"Token: {token[:35]}...")

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Probe GET endpoints for docs / discovery
get_urls = [
    "https://puppy.walmart.com/api/v1/sharing",
    "https://puppy.walmart.com/api/sharing",
    "https://puppy.walmart.com/api/v1/share-puppy/publish",
    "https://puppy.walmart.com/openapi.json",
    "https://puppy.walmart.com/api/docs",
    "https://puppy.walmart.com/api/v1",
    "https://puppy.walmart.com/sharing/s0m0660/rpc-dashboard",
]

for url in get_urls:
    try:
        r = requests.get(url, headers=headers, timeout=10, allow_redirects=True, verify=False)
        print(f"GET {r.status_code} {url}  ct={r.headers.get('content-type','?')[:40]}  body={r.text[:80]}")
    except Exception as ex:
        print(f"GET ERR {url}: {ex}")

# Try POST to common publish patterns with tiny test payload
post_urls = [
    "https://puppy.walmart.com/api/v1/sharing",
    "https://puppy.walmart.com/api/v1/sharing/publish",
    "https://puppy.walmart.com/api/sharing/publish",
]
payload = json.dumps({"name": "rpc-dashboard", "business": "rpc-ops", "content": "<h1>test</h1>"})
for url in post_urls:
    try:
        r = requests.post(url, data=payload, headers=headers, timeout=10, verify=False)
        print(f"POST {r.status_code} {url}  body={r.text[:120]}")
    except Exception as ex:
        print(f"POST ERR {url}: {ex}")
