"""Set premium_close_threshold on the near-expiration rule for BTG account.

Usage:
  python backend/scripts/set_premium_threshold.py

Requires local API running at http://localhost:8000 and the rule existing.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

BASE_URL = "http://localhost:8000"
EMAIL = "rubenilson12@gmail.com"
PASSWORD = "123456"
ACCOUNT_NAME = "BTG Pactual Investimentos"
TARGET_PREMIUM = 0.05  # R$ 0,05

NEAR_WINDOW = (3, 10)


def _req(method: str, path: str, token: Optional[str] = None, body: Optional[dict] = None) -> dict:
    url = BASE_URL + path
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code} {method} {path}: {msg}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error calling {method} {path}: {e}")


def login() -> str:
    data = _req("POST", "/auth/login", body={"email": EMAIL, "password": PASSWORD})
    token = data.get("access_token")
    if not token:
        raise RuntimeError("Login failed: no access_token in response")
    return token


def find_account_id(token: str, name: str) -> str:
    data = _req("GET", "/api/accounts", token=token)
    for acc in data.get("accounts", []):
        if acc.get("name", "").strip().lower() == name.strip().lower():
            return acc["id"]
    raise RuntimeError(f"Account not found by name: {name}")


def get_rules(token: str, account_id: str):
    data = _req("GET", f"/api/rules?account_id={account_id}", token=token)
    return data.get("rules", [])


def update_rule(token: str, rule_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    res = _req("PUT", f"/api/rules/{rule_id}", token=token, body=payload)
    return res.get("rule", res)


def main() -> int:
    print("Logging in...")
    token = login()
    print("Finding account by name...")
    account_id = find_account_id(token, ACCOUNT_NAME)
    print(f"Account id: {account_id}")

    rules = get_rules(token, account_id)
    near = None
    for r in rules:
        if r.get("dte_min") == NEAR_WINDOW[0] and r.get("dte_max") == NEAR_WINDOW[1]:
            near = r
            break

    if not near:
        raise RuntimeError("Near-expiration rule (3-10 DTE) not found. Run activate_near_rule.py first.")

    updated = update_rule(token, near["id"], {"premium_close_threshold": TARGET_PREMIUM})
    print(
        "Updated rule:",
        updated.get("id"),
        "premium_close_threshold=", updated.get("premium_close_threshold")
    )

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

