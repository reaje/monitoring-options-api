import httpx, asyncio

BASE='http://localhost:8001'

async def main():
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{BASE}/health")
            print('HEALTH', r.status_code, r.text[:100])
        except Exception as e:
            print('ERR', type(e).__name__, e)

if __name__ == '__main__':
    asyncio.run(main())

