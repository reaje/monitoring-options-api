"""Teste E2E autenticado usando provider MT5 (strict).

Fluxo:
1) /auth/login com email/senha de usuário → access_token
2) POST /api/mt5/heartbeat e /api/mt5/quotes com token do bridge (EA)
3) GET /api/market/quote/VALE3 com JWT do usuário → deve retornar 200 e source == "mt5"
"""

import json
import time
import sys
from typing import Tuple
from urllib import request, error

BASE = "http://127.0.0.1:8000"
USER_EMAIL = "rubenilson12@gmail.com"
USER_PASSWORD = "123456"

# Mesmo token usado no smoke test
BRIDGE_TOKEN = "oGHv0gBOC5tG47g4qYFlt99r0yxccz-kFHV5UW92Ka4"


def http_post(path: str, payload: dict, headers: dict) -> Tuple[int, str]:
    url = f"{BASE}{path}"
    data = json.dumps(payload).encode()
    req = request.Request(url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return resp.getcode(), body
    except error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return -1, str(e)


def http_get(path: str, headers: dict) -> Tuple[int, str]:
    url = f"{BASE}{path}"
    req = request.Request(url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return resp.getcode(), body
    except error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return -1, str(e)


def main() -> int:
    print("=" * 70)
    print("TESTE E2E AUTENTICADO • PROVIDER MT5 (STRICT)")
    print("=" * 70)

    # 1) Login de usuário
    print("\n1) Login de usuário...")
    sc, body = http_post(
        "/auth/login",
        {"email": USER_EMAIL, "password": USER_PASSWORD},
        {"Content-Type": "application/json"},
    )
    print("LOGIN:", sc, body[:200])
    if sc != 200:
        print("[FAIL] Login falhou")
        return 1

    try:
        token = json.loads(body).get("access_token")
    except Exception:
        token = None
    if not token:
        print("[FAIL] access_token não retornado")
        return 1

    user_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2) Enviar heartbeat e uma quote fresca via Bridge (EA)
    print("\n2) Enviando heartbeat e quote via Bridge (EA)...")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    hb = {
        "terminal_id": "QA-MT5",
        "account_number": "9001",
        "broker": "TEST",
        "build": 4150,
        "timestamp": now,
    }
    sc_hb, body_hb = http_post(
        "/api/mt5/heartbeat", hb, {"Content-Type": "application/json", "Authorization": f"Bearer {BRIDGE_TOKEN}"}
    )
    print("HEARTBEAT:", sc_hb, body_hb[:200])
    if sc_hb != 200:
        print("[FAIL] Heartbeat não aceito pelo backend")
        return 1

    quotes = {
        "terminal_id": "QA-MT5",
        "account_number": "9001",
        "quotes": [
            {
                "symbol": "VALE3",
                "bid": 62.70,
                "ask": 62.74,
                "last": 62.72,
                "volume": 1_000_000,
                "ts": now,
            }
        ],
    }
    sc_q, body_q = http_post(
        "/api/mt5/quotes", quotes, {"Content-Type": "application/json", "Authorization": f"Bearer {BRIDGE_TOKEN}"}
    )
    print("QUOTES:", sc_q, body_q[:200])
    if sc_q not in (200, 202):
        print("[FAIL] Quotes não aceitas pelo backend")
        return 1

    # 3) Consultar quote via rota autenticada (provider MT5)
    print("\n3) Consultando GET /api/market/quote/VALE3 (autenticado)...")
    sc_g, body_g = http_get("/api/market/quote/VALE3", {"Authorization": f"Bearer {token}"})
    print("QUOTE:", sc_g, body_g[:400])
    if sc_g != 200:
        print("[FAIL] Esperado 200, mas recebeu:", sc_g)
        return 1

    try:
        data = json.loads(body_g)
    except Exception:
        print("[FAIL] Resposta não é JSON válido")
        return 1

    if data.get("source") != "mt5":
        print("[FAIL] Esperado source='mt5', recebido:", data.get("source"))
        return 1

    print("\n[SUCCESS] E2E autenticado com MT5 concluído com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

