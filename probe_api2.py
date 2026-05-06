"""Round 2: figure out correct auth header + read OpenAPI spec."""
import configparser, pathlib, requests, json, urllib3
urllib3.disable_warnings()

cfg = configparser.ConfigParser()
cfg.read(pathlib.Path.home() / ".code_puppy" / "puppy.cfg")
token = cfg["puppy"]["puppy_token"].strip()

base = "https://puppy.walmart.com"
VERIFY = False

# ── 1. Read openapi spec ──────────────────────────────────────────────────
r = requests.get(f"{base}/openapi.json", verify=VERIFY, timeout=10)
if r.status_code == 200:
    spec = r.json()
    paths = list(spec.get("paths", {}).keys())
    print("OpenAPI paths:", json.dumps(paths[:30], indent=2))
else:
    print(f"openapi.json -> {r.status_code}: {r.text[:200]}")

# ── 2. Try every plausible auth header variant ───────────────────────────
auth_variants = {
    "Bearer":       {"Authorization": f"Bearer {token}"},
    "Token":        {"Authorization": f"Token {token}"},
    "X-Puppy-Token": {"X-Puppy-Token": token},
    "X-API-Key":    {"X-API-Key": token},
}

test_url = f"{base}/api/v1/sharing"
for name, hdrs in auth_variants.items():
    hdrs["Accept"] = "application/json"
    r = requests.get(test_url, headers=hdrs, verify=VERIFY, timeout=10)
    print(f"auth={name:20s} -> {r.status_code}  {r.text[:100]}")
