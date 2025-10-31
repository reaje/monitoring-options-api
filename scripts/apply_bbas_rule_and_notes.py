"""Apply account-wide roll rule for BTG and append BBAS3 monthly plan to notes.

- Logs in with dev credentials
- Finds account by name: "BTG Pactual Investimentos"
- Ensures there is an active account-wide rule with desired params (update if exactly one active; else create new)
- Finds OPEN BBAS3 CALL position and appends the monthly rolling plan to its notes

Usage:
  python backend/scripts/apply_bbas_rule_and_notes.py

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
TICKER = "BBAS3"

# Chosen rule params: align with monthly rolls/suggestions
RULE_PAYLOAD_BASE = {
    # Keep delta threshold conservative; omit if you want to ignore delta
    "delta_threshold": 0.60,
    # Use monthly horizon for suggestions (and alerts): 21–60 DTE
    "dte_min": 21,
    "dte_max": 60,
    # Target OTM window for covered calls
    "target_otm_pct_low": 0.02,
    "target_otm_pct_high": 0.06,
    # Notifications stay as-is; backend default is ["whatsapp", "sms"]
    "notify_channels": ["whatsapp", "sms"],
    "is_active": True,
}

PLAN_TEXT = (
    "Plano de Rolagem BBAS3 (venda de CALL coberta):\n"
    "1) Venda inicial: 27 CALL OTM, Strike 21,50, venc. 2025-11-14. Prêmio esperado: R$ 0,34 por ação.\n"
    "2) Derretimento (theta): se o prêmio cair abaixo de R$ 0,05, recomprar a CALL e lançar a próxima série.\n"
    "3) Rolagem mensal:\n"
    "   - Nov: Strike 22,50 (venc. 2025-12-12) → R$ 0,36\n"
    "   - Dez: Strike 23,00 (venc. 2026-01-16) → R$ 0,32\n"
    "   - Jan: Strike 23,50 (venc. 2026-02-13) → R$ 0,30\n"
    "   - Fev: Strike 24,00 (venc. 2026-03-13) → R$ 0,28\n"
    "   - Mar: Strike 24,50 (venc. 2026-04-10) → R$ 0,26\n"
    "4) Objetivo: cada opção virar pó (expirar sem valor) e repetir o processo para renda mensal.\n"
    "5) Resultado estimado: ganho acumulado ~ R$ 5.022 em 6 meses (~9,06% de retorno)."
)


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
    payload = {"email": EMAIL, "password": PASSWORD}
    data = _req("POST", "/auth/login", body=payload)
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


def ensure_rule(token: str, account_id: str) -> dict:
    # Check active rules first
    active = _req("GET", f"/api/rules/active?account_id={account_id}", token=token)
    rules = active.get("rules", [])

    payload = dict(RULE_PAYLOAD_BASE)
    payload["account_id"] = account_id

    if len(rules) == 1:
        rule_id = rules[0]["id"]
        updated = _req("PUT", f"/api/rules/{rule_id}", token=token, body=payload)
        return updated.get("rule", updated)
    else:
        # Create a new rule (do not toggle others implicitly)
        created = _req("POST", "/api/rules", token=token, body=payload)
        return created.get("rule", created)


def find_or_create_asset(token: str, account_id: str, ticker: str) -> str:
    assets = _req("GET", f"/api/assets?account_id={account_id}", token=token)
    for a in assets.get("assets", []):
        if a.get("ticker", "").upper() == ticker.upper():
            return a["id"]
    # Create
    created = _req("POST", "/api/assets", token=token, body={"ticker": ticker, "account_id": account_id})
    asset = created.get("asset") or created
    return asset.get("id")


def find_open_position(token: str, account_id: str, asset_id: str) -> Optional[dict]:
    data = _req("GET", f"/api/options?account_id={account_id}&status=OPEN", token=token)
    candidates: List[dict] = [
        p for p in data.get("positions", [])
        if p.get("asset_id") == asset_id and p.get("side") == "CALL"
    ]
    if not candidates:
        return None
    # Prefer the one with the known expiration first, if present
    preferred_exp = "2025-11-14"
    for p in candidates:
        if str(p.get("expiration", "")).startswith(preferred_exp):
            return p
    # Else return the most recent by created_at if available
    candidates.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return candidates[0]


def append_plan_to_notes(token: str, position: dict) -> dict:
    existing = position.get("notes") or ""
    # Avoid duplicating if already present
    if PLAN_TEXT.split("\n", 1)[0] in existing:
        return position  # assume already appended
    new_notes = (existing + "\n\n" if existing else "") + PLAN_TEXT
    position_id = position["id"]
    updated = _req("PUT", f"/api/options/{position_id}", token=token, body={"notes": new_notes})
    return updated.get("position", updated)


def main() -> int:
    print("Logging in...")
    token = login()
    print("Finding account by name...")
    account_id = find_account_id(token, ACCOUNT_NAME)
    print(f"Account id: {account_id}")

    print("Ensuring account-wide rule is set (active)...")
    rule = ensure_rule(token, account_id)
    print(f"Rule id: {rule.get('id')} | dte: {rule.get('dte_min')}-{rule.get('dte_max')} | otm: {rule.get('target_otm_pct_low')}-{rule.get('target_otm_pct_high')}")

    print("Locating BBAS3 asset and open CALL position...")
    asset_id = find_or_create_asset(token, account_id, TICKER)
    pos = find_open_position(token, account_id, asset_id)
    if not pos:
        print("WARNING: No OPEN BBAS3 CALL position found. Skipping notes update.")
        return 0

    print(f"Appending monthly plan to notes for position {pos.get('id')} (strike={pos.get('strike')}, exp={pos.get('expiration')})...")
    updated = append_plan_to_notes(token, pos)
    print("Notes updated.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

