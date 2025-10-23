from __future__ import annotations
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
EMAIL = "rubenilson12@gmail.com"
PASSWORD = "123456"


def http_post(url: str, data: dict, headers: dict | None = None) -> tuple[int, str]:
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.getcode(), resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def http_get(url: str, headers: dict | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.getcode(), resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def main() -> None:
    # Login
    status, body = http_post(f"{BASE}/auth/login", {"email": EMAIL, "password": PASSWORD})
    print("LOGIN:", status)
    if status != 200:
        print(body)
        return
    token = json.loads(body)["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Create account
    create_payload = {"name": "Conta Teste API", "broker": "XP", "account_number": "A1"}
    status, body = http_post(f"{BASE}/api/accounts", create_payload, headers)
    print("CREATE:", status)
    print(body)

    # List accounts
    status, body = http_get(f"{BASE}/api/accounts", headers)
    print("LIST:", status)
    print(body)


if __name__ == "__main__":
    main()

