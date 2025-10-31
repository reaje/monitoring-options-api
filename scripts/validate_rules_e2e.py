import json
import sys
import time
from datetime import datetime
import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

def pp(label, val):
    print(f"{label}:{val}")


def main():
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    email = f"qa.rolling+{ts}@example.com"
    pwd = "Test@12345!"

    print("START")
    pp("EMAIL", email)

    with httpx.Client(base_url=BASE, timeout=20.0, headers={"Content-Type": "application/json"}) as c:
        # 1) Register (best-effort)
        try:
            c.post("/auth/register", content=json.dumps({"email": email, "password": pwd, "name": "QA"}))
            print("REGISTER:created")
        except Exception as e:
            print(f"REGISTER:skip:{e}")

        # 2) Login
        r = c.post("/auth/login", content=json.dumps({"email": email, "password": pwd}))
        if r.status_code != 200:
            print("LOGIN_ERR:", r.status_code, r.text)
            print("END")
            return 2
        token = r.json().get("access_token")
        pp("TOKEN_PREFIX", token[:16])
        c.headers.update({"Authorization": f"Bearer {token}"})

        # 3) Create account
        r = c.post("/api/accounts/", content=json.dumps({"name": f"Conta QA Rolling {ts}"}))
        if r.status_code != 201:
            print("ACCOUNT_ERR:", r.status_code, r.text)
            print("END")
            return 3
        account_id = r.json()["account"]["id"]
        pp("ACCOUNT", account_id)

        # 4) Initial list
        initial_count = -1
        r = c.get(f"/api/rules/?account_id={account_id}")
        if r.status_code == 200:
            initial_count = len(r.json().get("rules", []))
            pp("INIT_COUNT", initial_count)
        else:
            pp("INIT_ERR", f"{r.status_code}")
            print("INIT_BODY:", r.text)

        # 5) Create two rules
        payload = {
            "account_id": account_id,
            "delta_threshold": 0.6,
            "dte_min": 3,
            "dte_max": 5,
            "spread_threshold": 5.0,
            "price_to_strike_ratio": 0.98,
            "min_volume": 1000,
            "max_spread": 0.05,
            "min_oi": 5000,
            "target_otm_pct_low": 0.03,
            "target_otm_pct_high": 0.08,
            "notify_channels": ["whatsapp", "sms"],
            "is_active": True,
        }

        # Rule 1
        r = c.post("/api/rules/", content=json.dumps(payload))
        if r.status_code == 201:
            pp("RULE1_ID", r.json()["rule"]["id"])
        else:
            pp("RULE1_ERR", f"{r.status_code}")
            print("RULE1_BODY:", r.text)

        # Rule 2
        r = c.post("/api/rules/", content=json.dumps(payload))
        if r.status_code == 201:
            pp("RULE2_ID", r.json()["rule"]["id"])
        else:
            pp("RULE2_ERR", f"{r.status_code}")
            print("RULE2_BODY:", r.text)

        # 6) Final list
        final_count = -1
        r = c.get(f"/api/rules/?account_id={account_id}")
        if r.status_code == 200:
            final_count = len(r.json().get("rules", []))
            pp("FINAL_COUNT", final_count)
        else:
            pp("FINAL_ERR", f"{r.status_code}")
            print("FINAL_BODY:", r.text)

        # 7) Aggregate list
        total_after = -1
        r = c.get("/api/rules/")
        if r.status_code == 200:
            total_after = r.json().get("total", -1)
            pp("TOTAL_AFTER", total_after)
        else:
            pp("TOTAL_ERR", f"{r.status_code}")
            print("TOTAL_BODY:", r.text)

        # 8) Summary JSON
        summary = {
            "email": email,
            "account_id": account_id,
            "initial_rules": initial_count,
            "final_rules": final_count,
            "total_after": total_after,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("END")
        return 0


if __name__ == "__main__":
    sys.exit(main())

