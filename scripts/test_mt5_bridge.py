import json
import os
import sys
import time
from urllib import request, error

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TOKEN = os.environ.get("MT5_BRIDGE_TOKEN", "CHANGE-ME-SET-A-STRONG-TOKEN")
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}",
}

def http_post(path: str, payload: dict) -> tuple[int, str]:
    url = f"{BASE}{path}"
    data = json.dumps(payload).encode()
    req = request.Request(url, data=data, headers=HEADERS, method="POST")
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return resp.getcode(), body
    except error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return -1, str(e)


def main() -> int:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    hb = {
        "terminal_id": "QA-MT5",
        "account_number": "9001",
        "broker": "TEST",
        "build": 4150,
        "timestamp": now,
    }
    sc, body = http_post("/api/mt5/heartbeat", hb)
    print("HEARTBEAT:", sc, body[:200])

    quotes = {
        "terminal_id": "QA-MT5",
        "account_number": "9001",
        "quotes": [
            {
                "symbol": "VALE3",
                "bid": 62.70,
                "ask": 62.74,
                "last": 62.72,
                "volume": 1000000,
                "ts": now,
            }
        ],
    }
    sc2, body2 = http_post("/api/mt5/quotes", quotes)
    print("QUOTES:", sc2, body2[:200])

    return 0


if __name__ == "__main__":
    sys.exit(main())

