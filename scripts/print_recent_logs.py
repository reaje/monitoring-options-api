from __future__ import annotations
import asyncio, os, sys
CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)
from app.database.repositories.alert_logs import AlertLogsRepository

async def main(target: str):
    digits = ''.join(ch for ch in target if ch.isdigit())
    logs = await AlertLogsRepository.get_recent_for_target(digits, minutes=60)
    for i, log in enumerate(logs[:10]):
        print(f"[{i+1}] channel={log['channel']} target={log['target']} status={log['status']}\nmessage=\n{log['message']}\n---\n")

if __name__ == '__main__':
    t = sys.argv[1] if len(sys.argv) > 1 else '5571991776091'
    asyncio.run(main(t))

