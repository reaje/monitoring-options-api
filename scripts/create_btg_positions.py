from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Tuple, Dict, Any, List
from datetime import date

BASE = "http://localhost:8000"
EMAIL = "rubenilson12@gmail.com"
PASSWORD = "123456"

ACCOUNT_NAME = "BTG Pactual Investimentos"
ACCOUNT_NUMBER = "004472007"

POSITIONS = [
    {
        "ticker": "BBAS3",
        "side": "CALL",
        "strategy": "COVERED_CALL",
        "strike": 21.50,
        "expiration": "2025-11-14",
        "quantity": 27,  # 2700 shares -> 27 contracts
        "avg_premium": 0.39,
        "notes": "Imported from BTG statement"
    },
    {
        "ticker": "VALE3",
        "side": "CALL",
        "strategy": "COVERED_CALL",
        "strike": 64.00,
        "expiration": "2025-10-31",
        "quantity": 7,   # 700 shares -> 7 contracts
        "avg_premium": 0.41,
        "notes": "Imported from BTG statement"
    }
]


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
    st, body = http_post(f"{BASE}/auth/login", {"email": EMAIL, "password": PASSWORD})
    print("LOGIN:", st)
    if st != 200:
        print(body)
        return 1
    token = json.loads(body)["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Resolve account
    st, ac_body = http_get(f"{BASE}/api/accounts", headers)
    print("ACCOUNTS_LIST:", st)
    if st != 200:
        print(ac_body)
        return 1
    accounts = json.loads(ac_body).get("accounts", [])
    account = next((a for a in accounts if a.get("account_number") == ACCOUNT_NUMBER or a.get("name") == ACCOUNT_NAME), None)
    if not account:
        print("Account not found")
        return 1
    account_id = account["id"]
    print("ACCOUNT_ID:", account_id)

    # Resolve assets for account
    st, as_body = http_get(f"{BASE}/api/assets?account_id={account_id}", headers)
    print("ASSETS_LIST:", st)
    if st != 200:
        print(as_body)
        return 1
    assets = json.loads(as_body).get("assets", [])
    by_ticker = {a["ticker"]: a for a in assets}

    # Existing positions to avoid duplicates (match by asset_id+strike+expiration+side)
    st, pos_list_body = http_get(f"{BASE}/api/options?account_id={account_id}", headers)
    print("POSITIONS_LIST:", st)
    if st != 200:
        print(pos_list_body)
        return 1
    existing = json.loads(pos_list_body).get("positions", [])

    def exists(payload: Dict[str, Any]) -> bool:
        for p in existing:
            if (
                p.get("asset_id") == payload.get("asset_id")
                and abs(float(p.get("strike")) - float(payload.get("strike"))) < 1e-6
                and str(p.get("expiration")) == str(payload.get("expiration"))
                and p.get("side") == payload.get("side")
            ):
                return True
        return False

    # Create positions
    for pos in POSITIONS:
        ticker = pos["ticker"]
        asset = by_ticker.get(ticker)
        if not asset:
            print(f"Asset {ticker} not found in account; skipping")
            continue
        payload = {
            "account_id": account_id,
            "asset_id": asset["id"],
            "side": pos["side"],
            "strategy": pos["strategy"],
            "strike": pos["strike"],
            "expiration": pos["expiration"],
            "quantity": pos["quantity"],
            "avg_premium": pos["avg_premium"],
            "notes": pos.get("notes"),
        }
        if exists(payload):
            print(f"POSITION_EXISTS:{ticker}:{pos['strike']}@{pos['expiration']}")
            continue
        st, create_body = http_post(f"{BASE}/api/options", payload, headers)
        print(f"CREATE_POSITION_{ticker}:", st)
        print(create_body)
        if st not in (200, 201):
            return 1

    # Final list
    st, pos_list_body2 = http_get(f"{BASE}/api/options?account_id={account_id}", headers)
    print("POSITIONS_LIST_FINAL:", st)
    print(pos_list_body2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

