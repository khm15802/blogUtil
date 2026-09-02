import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Settings
from .content_policy import ensure_non_political
from .db import Database
from .official_generator import CATEGORIES, SeoulFestivalCollector, download_official_poster
from .publisher import TistoryPublisher


class AutomationService:
    def __init__(self, config: Settings, db: Database):
        self.config = config
        self.db = db

    def next_category(self) -> str:
        previous = self.db.get_state("category_index")
        index = (int(previous or "-1") + 1) % len(CATEGORIES)
        self.db.set_state("category_index", str(index))
        return CATEGORIES[index]

    def create_draft(self) -> int:
        created = self.collect_drafts(1)
        if not created:
            raise RuntimeError("공식 사이트에서 새로 수집할 행사가 없습니다.")
        return created[0]

    def collect_drafts(self, count: int = 3) -> list[int]:
        posts = SeoulFestivalCollector().collect(self.db.recent_topic_keys(), count)
        created: list[int] = []
        for post in posts:
            try:
                ensure_non_political(post)
                download_official_poster(post, Path("active_log/assets"))
            except Exception:
                continue
            created.append(self.db.save_post(post))
        return created

    async def publish_private(self, post_id: int) -> str:
        if self.config.publish_visibility != "private":
            raise RuntimeError("1차 버전 안전장치: PUBLISH_VISIBILITY는 private이어야 합니다.")
        post = self.db.claim_post_for_publish(post_id)
        publisher = TistoryPublisher(
            self.config.blog_name, self.config.tistory_profile_dir, self.config.tistory_headless
        )
        image_paths = self.find_images(post["topic_key"])
        try:
            url = await publisher.publish_private(post, image_paths)
            self.db.update_publish_result(post_id, status="private", url=url)
            return url
        except Exception as exc:
            self.db.update_publish_result(post_id, status="failed", error=str(exc))
            raise

    async def publish_public(self, post_id: int) -> str:
        if self.config.publish_visibility != "public":
            raise RuntimeError("공개 게시를 사용하려면 PUBLISH_VISIBILITY=public이어야 합니다.")
        post = self.db.claim_post_for_publish(post_id)
        publisher = TistoryPublisher(
            self.config.blog_name, self.config.tistory_profile_dir, self.config.tistory_headless
        )
        image_paths = self.find_images(post["topic_key"])
        try:
            url = await publisher.publish(post, image_paths, visibility="public")
            self.db.update_publish_result(post_id, status="public", url=url)
            return url
        except Exception as exc:
            self.db.update_publish_result(post_id, status="failed", error=str(exc))
            raise

    def find_image(self, topic_key: str) -> Path | None:
        images = self.find_images(topic_key)
        return images[0] if images else None

    def find_images(self, topic_key: str) -> list[Path]:
        asset_dir = Path("active_log/assets")
        images: list[Path] = []
        for extension in (".jpg", ".jpeg", ".png", ".webp"):
            candidate = asset_dir / f"{topic_key}{extension}"
            if candidate.is_file():
                images.append(candidate)
                break
        for candidate in sorted(asset_dir.glob(f"{topic_key}-detail*")):
            if candidate.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                images.append(candidate)
        return images

    async def scheduled_cycle(self) -> int | None:
        """Publish one prepared draft without calling OpenAI.

        An empty queue is a normal state. The scheduler simply records the
        result and waits for its next randomized run.
        """
        post = await asyncio.to_thread(self.db.get_next_draft)
        if not post:
            self.db.set_state("last_cycle_result", "대기 중인 글 없음")
            return None
        if not self.config.auto_publish:
            self.db.set_state("last_cycle_result", "자동 등록 꺼짐")
            return None
        await self.publish_private(int(post["id"]))
        self.db.set_state("last_cycle_result", f"글 {post['id']} 비공개 등록 완료")
        return int(post["id"])

    def choose_next_run(self) -> datetime:
        tz = ZoneInfo(self.config.timezone)
        delay_seconds = random.randint(
            self.config.min_interval_days * 24 * 3600,
            self.config.max_interval_days * 24 * 3600,
        )
        return datetime.now(tz) + timedelta(seconds=delay_seconds)
