from __future__ import annotations
import asyncio, os, sys
from uuid import UUID
CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)
from app.database.repositories.alert_logs import AlertLogsRepository

async def main(alert_id: str):
    logs = await AlertLogsRepository.get_by_queue_id(UUID(alert_id))
    for i, l in enumerate(logs, 1):
        print(f"[{i}] channel={l['channel']} status={l['status']}")
        print('message=')
        print(l.get('message'))
        print('---')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python scripts/print_alert_logs_by_id.py <alert_id>')
    else:
        asyncio.run(main(sys.argv[1]))

