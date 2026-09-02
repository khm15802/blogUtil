from pathlib import Path
from datetime import datetime

from active_log.config import Settings
from active_log.db import Database
from active_log.generator import CATEGORIES
from active_log.service import AutomationService
from active_log.renderer import PostRenderer
from active_log.sample_data import running_schedule_sample
from active_log.image_manager import attach_tistory_tags
from active_log.content_policy import ensure_non_political


def _queued_post(topic_key: str, title: str) -> dict:
    return {
        "topic_key": topic_key,
        "category": "행사·이벤트",
        "title": title,
        "summary": "공식 정보를 확인한 테스트 글입니다.",
        "content_html": "<p>테스트 본문</p>",
        "tags": ["테스트"],
        "sources": ["https://example.com/official"],
    }


def test_category_rotation(tmp_path: Path):
    config = Settings(database_path=tmp_path / "test.db")
    service = AutomationService(config, Database(config.database_path))
    assert [service.next_category() for _ in CATEGORIES] == CATEGORIES
    assert service.next_category() == CATEGORIES[0]


def test_collect_drafts_saves_only_safe_posts(monkeypatch, tmp_path: Path):
    config = Settings(database_path=tmp_path / "collect.db")
    service = AutomationService(config, Database(config.database_path))
    posts = [
        _queued_post("safe-event", "서울 생활 체육 행사 안내"),
        _queued_post("blocked-event", "국회의원 선거 기념 행사"),
    ]
    for post in posts:
        post["poster_url"] = "https://example.com/poster.jpg"
    monkeypatch.setattr("active_log.service.SeoulFestivalCollector.collect", lambda *_args, **_kwargs: posts)
    monkeypatch.setattr("active_log.service.download_official_poster", lambda *_args, **_kwargs: None)
    ids = service.collect_drafts(3)
    assert len(ids) == 1
    assert service.db.get_post(ids[0])["topic_key"] == "safe-event"


def test_next_run_is_within_configured_range(tmp_path: Path):
    config = Settings(database_path=tmp_path / "test.db", min_interval_days=1, max_interval_days=3)
    service = AutomationService(config, Database(config.database_path))
    run_at = service.choose_next_run()
    delta_days = (run_at - datetime.now(run_at.tzinfo)).total_seconds() / 86400
    assert 0.99 <= delta_days <= 3.01


def test_public_mode_is_rejected(tmp_path: Path):
    config = Settings(database_path=tmp_path / "test.db", publish_visibility="public")
    service = AutomationService(config, Database(config.database_path))
    try:
        import asyncio
        asyncio.run(service.publish_private(1))
    except RuntimeError as exc:
        assert "private" in str(exc)
    else:
        raise AssertionError("public 모드는 거부되어야 합니다")


def test_public_publish_requires_public_mode(tmp_path: Path):
    import asyncio

    config = Settings(database_path=tmp_path / "test.db", publish_visibility="private")
    service = AutomationService(config, Database(config.database_path))
    try:
        asyncio.run(service.publish_public(1))
    except RuntimeError as exc:
        assert "public" in str(exc)
    else:
        raise AssertionError("private 설정에서는 공개 게시를 거부해야 합니다")


def test_sample_export_separates_data_and_template(tmp_path: Path):
    post = running_schedule_sample()
    html_path = PostRenderer().export(post, tmp_path / "output")
    rendered = html_path.read_text(encoding="utf-8")
    assert "2026 하반기 전국 러닝 대회 일정 총정리" in rendered
    assert "max-width:860px" in rendered
    assert "ACTIVELOG_IMAGE:hero" in rendered
    assert (tmp_path / "output" / "post-data.json").is_file()
    assert (tmp_path / "output" / "images").is_dir()


def test_tistory_tag_is_matched_by_filename():
    post = running_schedule_sample()
    tag = '[##_Image|kage@example/img.png|CDM|1.3|{"originWidth":1536,"originHeight":515,"style":"alignCenter","filename":"01_대표_도심_러닝.png"}_##]'
    updated, missing = attach_tistory_tags(post, tag)
    assert updated.image_by_slot("hero").tistory_tag == tag
    assert "02_9월_강변_러닝.png" in missing


def test_draft_queue_is_fifo(tmp_path: Path):
    db = Database(tmp_path / "queue.db")
    first_id = db.save_post(_queued_post("first-post", "첫 번째 글"))
    db.save_post(_queued_post("second-post", "두 번째 글"))

    assert db.count_drafts() == 2
    assert db.get_next_draft()["id"] == first_id

    db.update_publish_result(first_id, status="private", url="https://example.com/1")
    assert db.count_drafts() == 1
    assert db.get_next_draft()["topic_key"] == "second-post"


def test_scheduled_cycle_does_not_call_openai(tmp_path: Path):
    import asyncio

    config = Settings(database_path=tmp_path / "scheduled.db", auto_publish=True)
    db = Database(config.database_path)
    post_id = db.save_post(_queued_post("queued-post", "대기 글"))
    service = AutomationService(config, db)
    published: list[int] = []

    async def fake_publish(candidate_id: int) -> str:
        published.append(candidate_id)
        db.update_publish_result(candidate_id, status="private", url="https://example.com/private")
        return "https://example.com/private"

    service.publish_private = fake_publish
    result = asyncio.run(service.scheduled_cycle())

    assert result == post_id
    assert published == [post_id]
    assert db.get_post(post_id)["status"] == "private"


def test_empty_queue_is_a_normal_scheduled_cycle(tmp_path: Path):
    import asyncio

    config = Settings(database_path=tmp_path / "empty.db", auto_publish=True)
    db = Database(config.database_path)
    service = AutomationService(config, db)

    assert asyncio.run(service.scheduled_cycle()) is None
    assert db.get_state("last_cycle_result") == "대기 중인 글 없음"


def test_saved_draft_can_be_edited(tmp_path: Path):
    db = Database(tmp_path / "edit.db")
    post_id = db.save_post(_queued_post("before", "수정 전 제목"))
    updated = _queued_post("after", "수정 후 제목")

    db.update_post(post_id, updated)

    post = db.get_post(post_id)
    assert post["topic_key"] == "after"
    assert post["title"] == "수정 후 제목"
    assert post["status"] == "draft"


def test_published_post_edit_does_not_requeue_it(tmp_path: Path):
    db = Database(tmp_path / "published-edit.db")
    post_id = db.save_post(_queued_post("published", "게시 완료"))
    db.update_publish_result(post_id, status="private", url="https://example.com/private")

    db.update_post(post_id, _queued_post("published-edited", "게시 후 수정"))

    post = db.get_post(post_id)
    assert post["status"] == "private"
    assert post["tistory_url"] == "https://example.com/private"
    assert db.count_drafts() == 0


def test_only_one_worker_can_claim_a_draft(tmp_path: Path):
    db = Database(tmp_path / "claim.db")
    post_id = db.save_post(_queued_post("claim-once", "한 번만 게시"))

    claimed = db.claim_post_for_publish(post_id)
    assert claimed["status"] == "publishing"

    try:
        db.claim_post_for_publish(post_id)
    except RuntimeError as exc:
        assert "publishing" in str(exc)
    else:
        raise AssertionError("이미 선점된 글은 다시 선점할 수 없어야 합니다")


def test_posts_can_be_listed_oldest_first(tmp_path: Path):
    db = Database(tmp_path / "order.db")
    first = db.save_post(_queued_post("order-first", "첫 글"))
    second = db.save_post(_queued_post("order-second", "둘째 글"))
    assert [row["id"] for row in db.list_posts(oldest_first=True)] == [first, second]
    assert [row["id"] for row in db.list_posts()] == [second, first]


def test_draft_can_be_deleted_but_publishing_post_cannot(tmp_path: Path):
    db = Database(tmp_path / "delete.db")
    draft_id = db.save_post(_queued_post("delete-draft", "삭제할 글"))
    db.delete_post(draft_id)
    assert db.get_post(draft_id) is None

    publishing_id = db.save_post(_queued_post("keep-publishing", "게시 중 글"))
    db.claim_post_for_publish(publishing_id)
    try:
        db.delete_post(publishing_id)
    except RuntimeError as exc:
        assert "게시 중" in str(exc)
    else:
        raise AssertionError("게시 중인 글은 삭제되지 않아야 합니다")


def test_political_post_is_rejected_before_save():
    post = _queued_post("political-event", "국회의원 선거 기념 행사")
    try:
        ensure_non_political(post)
    except RuntimeError as exc:
        assert "정치 관련" in str(exc)
    else:
        raise AssertionError("정치 관련 글은 거부되어야 합니다")
