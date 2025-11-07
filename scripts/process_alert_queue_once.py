import asyncio
import json
import os
import sys
from typing import Optional

# Ensure 'backend' parent dir is on sys.path so 'app' package can be imported
CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from app.services.notification_service import notification_service
from app.core.logger import logger


async def main(limit: Optional[int] = None):
    try:
        res = await notification_service.process_pending_alerts(limit or 100)
        print(json.dumps(res))
    except Exception as e:
        logger.error("Process queue failed", error=str(e))
        raise


if __name__ == "__main__":
    import sys
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    asyncio.run(main(lim))

