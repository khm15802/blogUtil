from datetime import date
from email.message import Message
from pathlib import Path

import active_log.official_generator as module
from active_log.official_generator import OfficialPostGenerator, SeoulFestivalCollector, download_official_poster


def test_official_generator_creates_draft_without_api_key():
    post = OfficialPostGenerator().generate([], today=date(2026, 9, 1))
    assert post["topic_key"] == "seoul-fireworks-festival-2026"
    assert post["sources"][0]["url"].startswith("https://festival.seoul.go.kr/")
    assert "OPENAI" not in post["content_html"]
    assert "공식 축제 페이지" in post["content_html"]


def test_official_generator_skips_recent_and_finished_events():
    post = OfficialPostGenerator().generate(
        ["seoul-fireworks-festival-2026"], today=date(2026, 9, 6)
    )
    assert post["topic_key"] == "seoul-sculpture-festival-2026"


def test_official_poster_is_saved_with_topic_key(monkeypatch, tmp_path: Path):
    headers = Message()
    headers["Content-Type"] = "image/jpg"

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, _limit):
            return b"poster"

    response = Response()
    response.headers = headers
    monkeypatch.setattr(module, "urlopen", lambda *_args, **_kwargs: response)
    post = {"topic_key": "official-event", "poster_url": "https://example.com/poster"}
    path = download_official_poster(post, tmp_path)
    assert path == tmp_path / "official-event.jpg"
    assert path.read_bytes() == b"poster"


def test_seoul_collector_discovers_and_parses_official_event():
    main = '<a href="/festival/main/festivalView.do?festacode=901">행사</a>'
    detail = """
    <img src="/cmmn/file/getImage.do?atchFileId=poster&thumb=Y" alt="공식 포스터">
    <h2 class="title">2026 서울 생활체육축제</h2>
    <dl><dt>기간</dt><dd>2026-09-10 ~ 2026-09-12</dd>
    <dt>시간</dt><dd>10:00 ~ 18:00</dd><dt>장소</dt><dd>서울광장</dd>
    <dt>요금</dt><dd>무료</dd></dl>
    """
    collector = SeoulFestivalCollector(fetch=lambda url: main if url.endswith("festivalMain.do") else detail)
    posts = collector.collect([], 3, today=date(2026, 9, 1))
    assert len(posts) == 1
    assert posts[0]["topic_key"] == "seoul-festival-901"
    assert posts[0]["title"].startswith("2026 서울 생활체육축제")
    assert posts[0]["poster_url"].startswith("https://festival.seoul.go.kr/")
    assert "/cmmn/file/getImage.do?" in posts[0]["poster_url"]


def test_seoul_collector_skips_duplicate_and_finished_event():
    main = '<a href="festivalView.do?festacode=901">행사</a>'
    collector = SeoulFestivalCollector(fetch=lambda _url: main)
    assert collector.collect(["seoul-festival-901"], 3, today=date(2026, 9, 1)) == []
