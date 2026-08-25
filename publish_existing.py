import asyncio

from active_log.config import settings
from active_log.db import Database
from active_log.service import AutomationService


async def main() -> None:
    db = Database(settings.database_path)
    service = AutomationService(settings, db)
    for post_id in (6, 7, 8, 9):
        post = db.get_post(post_id)
        if not post or post["status"] == "private":
            continue
        print(f"publishing {post_id}: {post['title']}")
        url = await service.publish_private(post_id)
        print(f"saved private: {url}")


if __name__ == "__main__":
    asyncio.run(main())
