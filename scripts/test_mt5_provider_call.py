import asyncio
import os
import sys

# Add project root (backend) to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.services.market_data import market_data_provider

async def main():
    q = await market_data_provider.get_quote("VALE3")
    print("PROVIDER_QUOTE:", {k: q.get(k) for k in ("symbol","current_price","bid","ask","timestamp","source")})

if __name__ == "__main__":
    asyncio.run(main())

