from __future__ import annotations
import json
import sys
import urllib.request
import urllib.error
from typing import Tuple, Dict, Any

BASE = "http://localhost:8000"
EMAIL = "rubenilson12@gmail.com"
PASSWORD = "123456"

ACCOUNT_NAME = "BTG Pactual Investimentos"
BROKER = "BTG Pactual Investimentos"
ACCOUNT_NUMBER = "004472007"
ASSETS = ["BBAS3", "VALE3"]


def http_post(url: str, data: dict, headers: dict | None = None) -> Tuple[int, str]:
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.getcode(), resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def http_get(url: str, headers: dict | None = None) -> Tuple[int, str]:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.getcode(), resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def main() -> int:
    # Login
    status, body = http_post(f"{BASE}/auth/login", {"email": EMAIL, "password": PASSWORD})
    print("LOGIN:", status)
    if status != 200:
        print(body)
        return 1
    token = json.loads(body)["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # List accounts and reuse if exists
    status, acc_list_body = http_get(f"{BASE}/api/accounts", headers)
    print("ACCOUNTS_LIST:", status)
    if status != 200:
        print(acc_list_body)
        return 1
    acc_list = json.loads(acc_list_body).get("accounts", [])
    account = next((a for a in acc_list if a.get("account_number") == ACCOUNT_NUMBER or a.get("name") == ACCOUNT_NAME), None)

    if account is None:
        # Create account
        create_payload = {"name": ACCOUNT_NAME, "broker": BROKER, "account_number": ACCOUNT_NUMBER}
        status, body = http_post(f"{BASE}/api/accounts", create_payload, headers)
        print("ACCOUNT_CREATE:", status)
        print(body)
        if status not in (200, 201):
            return 1
        account = json.loads(body).get("account") or {}

    account_id = account.get("id")
    print("ACCOUNT_ID:", account_id)
    if not account_id:
        print("Failed to resolve account id")
        return 1

    # Ensure assets exist
    status, assets_body = http_get(f"{BASE}/api/assets?account_id={account_id}", headers)
    print("ASSETS_LIST:", status)
    if status != 200:
        print(assets_body)
        return 1
    existing_assets = {a.get("ticker") for a in json.loads(assets_body).get("assets", [])}

    for ticker in ASSETS:
        if ticker in existing_assets:
            print(f"ASSET_EXISTS:{ticker}")
            continue
        status, create_asset_body = http_post(f"{BASE}/api/assets", {"ticker": ticker, "account_id": account_id}, headers)
        print(f"ASSET_CREATE_{ticker}:", status)
        print(create_asset_body)
        if status not in (200, 201):
            print(f"Failed to create asset {ticker}")
            return 1

    # Final list
    status, assets_body2 = http_get(f"{BASE}/api/assets?account_id={account_id}", headers)
    print("ASSETS_LIST_FINAL:", status)
    print(assets_body2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

