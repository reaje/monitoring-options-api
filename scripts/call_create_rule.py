import asyncio
import httpx
from datetime import datetime

BASE = "http://localhost:8000"

async def main():
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    email = f"qa.rolling+{ts}@example.com"
    pwd = "Test@12345!"
    async with httpx.AsyncClient(timeout=10) as client:
        # Register
        try:
            await client.post(f"{BASE}/auth/register", json={"email": email, "password": pwd, "name": "QA"})
        except Exception:
            pass
        # Login
        r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": pwd})
        tok = r.json()["access_token"]
        hdr = {"Authorization": f"Bearer {tok}"}
        # Create account
        r = await client.post(f"{BASE}/api/accounts/", headers=hdr, json={"name": "Conta QA"})
        aid = r.json()["account"]["id"]
        # Create rule
        payload = {
            "account_id": aid,
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
            "notify_channels": ["whatsapp","sms"],
            "is_active": True,
        }
        r = await client.post(f"{BASE}/api/rules/", headers=hdr, json=payload)
        print("STATUS:", r.status_code)
        print("BODY:", r.text)

if __name__ == "__main__":
    asyncio.run(main())

