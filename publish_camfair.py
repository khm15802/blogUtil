import asyncio
from pathlib import Path

from active_log.config import settings
from active_log.db import Database
from active_log.publisher import TistoryPublisher


async def main() -> None:
    db = Database(settings.database_path)
    post = next(
        item for item in db.list_posts(100)
        if item["topic_key"] == "event-camfair-gyeongnam-2026"
    )
    publisher = TistoryPublisher(
        settings.blog_name, settings.tistory_profile_dir, settings.tistory_headless
    )
    url = await publisher.publish_private(
        post, Path("active_log/assets/event-camfair-gyeongnam-2026.jpg")
    )
    db.update_publish_result(post["id"], status="private", url=url)
    print(f"published post_id={post['id']} url={url}")


if __name__ == "__main__":
    asyncio.run(main())
