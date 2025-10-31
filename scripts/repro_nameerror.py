import asyncio, json
from uuid import UUID
from pathlib import Path
import sys

# Ensure backend package is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.repositories.rules import RulesRepository
from app.config import settings

async def main():
    print('SCHEMA:', settings.DB_SCHEMA)
    # Just test building a connection which references settings.
    try:
        conn = await RulesRepository._get_conn(auth_user_id=str(UUID('00000000-0000-0000-0000-000000000001')))
        await conn.close()
        print('CONN_OK')
    except Exception as e:
        print('CONN_ERR:', e)

if __name__ == '__main__':
    asyncio.run(main())

