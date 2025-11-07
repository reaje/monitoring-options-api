from __future__ import annotations
import asyncio, os, sys
CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)
from app.services.market_data.brapi_provider import brapi_provider

async def main(ticker: str):
    q = await brapi_provider.get_quote(ticker)
    print(q)

if __name__ == '__main__':
    t = sys.argv[1] if len(sys.argv) > 1 else 'BBAS3'
    asyncio.run(main(t))

