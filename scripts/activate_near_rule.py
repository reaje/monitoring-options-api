"""Ensure a 'near-expiration' roll rule exists for BTG account and activate it,
while deactivating the monthly window rule.

- Near-expiration window: DTE 3–10
- Monthly window (to deactivate now): DTE 21–60

Usage:
  python backend/scripts/activate_near_rule.py

Requires local API running at http://localhost:8000
"""
from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

BASE_URL = "http://localhost:8000"
EMAIL = "rubenilson12@gmail.com"
PASSWORD = "123456"
ACCOUNT_NAME = "BTG Pactual Investimentos"

NEAR_CONF = {
    "delta_threshold": 0.60,
    "dte_min": 3,
    "dte_max": 10,
    "target_otm_pct_low": 0.02,
    "target_otm_pct_high": 0.06,
    "is_active": True,
}
MONTHLY_RANGE = (21, 60)


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


def get_rules(token: str, account_id: str) -> List[Dict[str, Any]]:
    data = _req("GET", f"/api/rules?account_id={account_id}", token=token)
    return data.get("rules", [])


def create_rule(token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    res = _req("POST", "/api/rules", token=token, body=payload)
    return res.get("rule", res)


def update_rule(token: str, rule_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    res = _req("PUT", f"/api/rules/{rule_id}", token=token, body=payload)
    return res.get("rule", res)


def ensure_near_rule_and_toggle(token: str, account_id: str) -> Dict[str, Any]:
    rules = get_rules(token, account_id)

    # Find near-expiration rule (DTE 3-10)
    near = None
    for r in rules:
        if r.get("dte_min") == NEAR_CONF["dte_min"] and r.get("dte_max") == NEAR_CONF["dte_max"]:
            near = r
            break

    if not near:
        payload = dict(NEAR_CONF)
        payload["account_id"] = account_id
        near = create_rule(token, payload)
        print(f"Created near-expiration rule: {near.get('id')}")

    # Activate near rule if not active
    if not near.get("is_active", False):
        near = update_rule(token, near["id"], {"is_active": True})
        print(f"Activated near-expiration rule: {near.get('id')}")

    # Deactivate monthly rule (21-60) if present and different from near
    for r in rules:
        if r["id"] == near["id"]:
            continue
        if r.get("dte_min") == MONTHLY_RANGE[0] and r.get("dte_max") == MONTHLY_RANGE[1]:
            if r.get("is_active"):
                update_rule(token, r["id"], {"is_active": False})
                print(f"Deactivated monthly rule: {r['id']}")

    return near


def main() -> int:
    print("Logging in...")
    token = login()
    print("Finding account by name...")
    account_id = find_account_id(token, ACCOUNT_NAME)
    print(f"Account id: {account_id}")

    print("Ensuring near-expiration rule is active and monthly is deactivated...")
    near = ensure_near_rule_and_toggle(token, account_id)
    print(
        "Near rule:",
        near.get("id"),
        f"dte={near.get('dte_min')}-{near.get('dte_max')} active={near.get('is_active')}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

