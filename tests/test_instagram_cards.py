from pathlib import Path

from PySide6.QtGui import QImage

from active_log.instagram_cards import CARD_HEIGHT, CARD_WIDTH, build_cards, generate_instagram_cards


def sample_post() -> dict:
    return {
        "topic_key": "sample-event",
        "category": "캠핑·레저",
        "title": "2026 샘플 캠핑 행사",
        "summary": "공식 정보를 기준으로 정리한 행사입니다.",
        "content_html": """
        <table><tr><td><strong>기간</strong></td><td>2026-10-09 ~ 2026-10-11</td></tr>
        <tr><td><strong>장소</strong></td><td>일산 킨텍스</td></tr>
        <tr><td><strong>운영 시간</strong></td><td>10:00~18:00</td></tr>
        <tr><td><strong>주요 프로그램</strong></td><td>캠핑 장비 전시</td></tr>
        <tr><td><strong>관람료</strong></td><td>공식 안내 확인</td></tr></table>
        """,
        "sources": [{"title": "공식 행사 안내", "url": "https://example.com"}],
    }


def test_build_cards_uses_existing_post_information():
    cards = build_cards(sample_post())
    assert len(cards) == 6
    assert "2026-10-09" in cards[1].body
    assert "일산 킨텍스" in cards[2].body
    assert "캠핑 장비 전시" in cards[4].body


def test_generate_instagram_cards_creates_six_portrait_pngs(tmp_path: Path):
    paths = generate_instagram_cards(sample_post(), tmp_path)
    assert [path.name for path in paths] == [f"{index:02d}.png" for index in range(1, 7)]
    assert all(QImage(str(path)).size().toTuple() == (CARD_WIDTH, CARD_HEIGHT) for path in paths)
    assert (tmp_path / "caption.txt").is_file()
    assert "01.png부터 06.png" in (tmp_path / "업로드-안내.txt").read_text(encoding="utf-8")
