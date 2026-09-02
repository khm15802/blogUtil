from __future__ import annotations

import html
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


CATEGORIES = ["러닝", "자전거", "캠핑·레저", "행사·이벤트"]
SEOUL_FESTIVAL_MAIN_URL = "https://festival.seoul.go.kr/festival/main/festivalMain.do"
SEOUL_FESTIVAL_BASE_URL = "https://festival.seoul.go.kr"

# 서울시 공식 축제 페이지에서 2026-09-01에 확인한 행사만 사용한다.
# 정보가 바뀔 수 있으므로 본문에는 항상 공식 페이지 재확인 안내를 넣는다.
OFFICIAL_EVENTS = (
    {
        "topic_key": "seoul-fireworks-festival-2026",
        "category": "행사·이벤트",
        "title": "서울세계불꽃축제 2026 일정·장소·관람 정보",
        "summary": "여의도와 이촌한강공원 일대에서 열리는 서울세계불꽃축제의 일정과 방문 전 확인할 정보를 정리했습니다.",
        "start_date": "2026-09-04",
        "end_date": "2026-09-05",
        "place": "여의도 및 이촌한강공원 일대",
        "time": "13:00~21:00 (9월 4일 전야제, 9월 5일 불꽃쇼)",
        "fee": "관람 구역별 요금과 무료 관람 가능 구역은 공식 안내에서 확인",
        "program": "전야제, 세계 초청 불꽃쇼, 시민 참여 프로그램",
        "official_url": "https://festival.seoul.go.kr/festival/main/festivalView.do?festacode=379",
        "poster_url": "https://festival.seoul.go.kr/cmmn/file/getImage.do?atchFileId=3828da71efe34a5fa5edb8d65126a4af&thumb=Y",
        "tags": ["서울세계불꽃축제", "서울축제", "한강축제", "2026서울행사"],
    },
    {
        "topic_key": "seoul-sculpture-festival-2026",
        "category": "행사·이벤트",
        "title": "제3회 서울조각페스티벌 일정·장소·관람 정보",
        "summary": "열린송현녹지광장과 뚝섬한강공원에서 열리는 서울조각페스티벌의 전시 기간과 프로그램 정보를 정리했습니다.",
        "start_date": "2026-08-29",
        "end_date": "2026-11-30",
        "place": "열린송현녹지광장, 뚝섬한강공원",
        "time": "전시는 상시 운영, 프로그램 운영 시간은 공식 페이지 확인",
        "fee": "무료",
        "program": "야외 조각 전시, 조각마을, 공연과 체험 프로그램",
        "official_url": "https://festival.seoul.go.kr/festival/main/festivalView.do?festacode=393",
        "poster_url": "https://festival.seoul.go.kr/cmmn/file/getImage.do?atchFileId=def5f829e21940f79a0979de9a475325&thumb=Y",
        "tags": ["서울조각페스티벌", "서울전시", "야외전시", "2026서울행사"],
    },
    {
        "topic_key": "seoul-hanok-week-2026",
        "category": "행사·이벤트",
        "title": "2026 서울한옥위크 기간·장소·프로그램 안내",
        "summary": "북촌과 서촌 등 서울 한옥마을에서 열리는 서울한옥위크의 기간과 주요 프로그램을 정리했습니다.",
        "start_date": "2026-10-02",
        "end_date": "2026-10-11",
        "place": "북촌 및 서촌 등 서울 한옥마을 일대",
        "time": "프로그램별 운영 시간은 공식 페이지 확인",
        "fee": "프로그램별 공식 안내 확인",
        "program": "한옥 전시, 도슨트 투어, 체험, 공연과 시민 참여 프로그램",
        "official_url": "https://festival.seoul.go.kr/festival/main/festivalView.do?festacode=479",
        "poster_url": "https://festival.seoul.go.kr/cmmn/file/getImage.do?atchFileId=5d8c4e8289ca407cbfa8ac8db49cd343&thumb=Y",
        "tags": ["서울한옥위크", "북촌", "서촌", "서울문화행사"],
    },
)


class OfficialPostGenerator:
    """Create a factual draft from a small, verified official-event catalog."""

    def generate(self, recent_keys: list[str], *, today: date | None = None) -> dict:
        checked = today or date.today()
        event = next(
            (
                item
                for item in OFFICIAL_EVENTS
                if date.fromisoformat(item["end_date"]) >= checked
                and item["topic_key"] not in recent_keys
            ),
            None,
        )
        if event is None:
            raise RuntimeError(
                "현재 공식 자료에서 새로 만들 수 있는 행사가 없습니다. "
                "확인된 행사를 추가한 뒤 다시 시도하세요."
            )

        escaped = {key: html.escape(str(value)) for key, value in event.items() if isinstance(value, str)}
        content = f"""
<p>{escaped['summary']}</p>
<p style="padding:18px;background:#f3faf5;border-left:4px solid #16a34a;"><strong>공식 안내</strong><br><a href="{escaped['official_url']}" target="_blank" rel="noopener"><strong>서울시 공식 축제 페이지에서 최신 정보 확인하기 →</strong></a></p>
<h2>행사 핵심 정보</h2>
<table data-ke-style="style12"><tbody>
<tr><td><strong>기간</strong></td><td>{escaped['start_date']} ~ {escaped['end_date']}</td></tr>
<tr><td><strong>장소</strong></td><td>{escaped['place']}</td></tr>
<tr><td><strong>운영 시간</strong></td><td>{escaped['time']}</td></tr>
<tr><td><strong>주요 프로그램</strong></td><td>{escaped['program']}</td></tr>
<tr><td><strong>관람료</strong></td><td>{escaped['fee']}</td></tr>
</tbody></table>
<h2>방문 전에 확인할 것</h2>
<ul><li>행사 당일 운영 여부와 프로그램 시간</li><li>사전 신청 또는 유료 관람 구역 여부</li><li>대중교통과 교통 통제 안내</li><li>우천·기상 상황에 따른 변경 공지</li></ul>
<h2>참고 및 공식 안내</h2>
<p><a href="{escaped['official_url']}" target="_blank" rel="noopener">서울시 공식 축제 안내 바로가기</a></p>
<p><small>정보 확인일: {checked:%Y.%m.%d}. 일정과 운영 내용은 변경될 수 있으므로 방문 직전에 공식 페이지를 다시 확인하세요.</small></p>
""".strip()
        return {
            "topic_key": event["topic_key"],
            "category": event["category"],
            "title": event["title"],
            "summary": event["summary"],
            "content_html": content,
            "tags": list(event["tags"]),
            "sources": [{"title": "서울시 공식 축제 안내", "url": event["official_url"]}],
            "poster_url": event["poster_url"],
        }


class _FestivalDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.poster_path = ""
        self.fields: dict[str, str] = {}
        self._capture_tag = ""
        self._buffer: list[str] = []
        self._current_label = ""

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if tag == "img" and not self.poster_path:
            source = attributes.get("src", "")
            if "/cmmn/file/getImage.do" in source:
                self.poster_path = source
        if tag == "h2" and "title" in attributes.get("class", "").split() and not self.title:
            self._capture_tag = "h2"
            self._buffer = []
        elif tag in {"dt", "dd"}:
            self._capture_tag = tag
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture_tag:
            text = " ".join(data.split())
            if text:
                self._buffer.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag != self._capture_tag:
            return
        value = " ".join(self._buffer).strip()
        if tag == "h2" and value:
            self.title = value
        elif tag == "dt":
            self._current_label = value
        elif tag == "dd" and self._current_label and value:
            self.fields[self._current_label] = value
        self._capture_tag = ""
        self._buffer = []


class SeoulFestivalCollector:
    """Collect unpublished events from Seoul's official festival pages."""

    def __init__(self, fetch=None):
        self.fetch = fetch or self._fetch

    @staticmethod
    def _fetch(url: str) -> str:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 ActiveLog/0.1"})
        with urlopen(request, timeout=20) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read(2 * 1024 * 1024).decode(charset, "replace")

    def discover_urls(self) -> list[str]:
        page = self.fetch(SEOUL_FESTIVAL_MAIN_URL)
        codes = re.findall(r"festivalView\.do[^\"']*?festacode(?:=|%3D)(\d+)", page)
        unique_codes = list(dict.fromkeys(codes))
        if not unique_codes:
            raise RuntimeError("서울시 공식 축제 목록에서 행사 링크를 찾지 못했습니다.")
        return [
            f"{SEOUL_FESTIVAL_BASE_URL}/festival/main/festivalView.do?festacode={code}"
            for code in unique_codes
        ]

    def parse_event(self, url: str) -> dict:
        parser = _FestivalDetailParser()
        parser.feed(self.fetch(url))
        match = re.search(r"festacode=(\d+)", url)
        period = parser.fields.get("기간", "")
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", period)
        if not match or not parser.title or len(dates) < 2 or not parser.poster_path:
            raise RuntimeError("공식 행사 페이지의 필수 정보를 읽지 못했습니다.")
        poster_url = urljoin(SEOUL_FESTIVAL_BASE_URL, parser.poster_path)
        if not poster_url.startswith(f"{SEOUL_FESTIVAL_BASE_URL}/cmmn/file/getImage.do?"):
            raise RuntimeError("공식 행사 대표 포스터 주소가 아닙니다.")
        return {
            "topic_key": f"seoul-festival-{match.group(1)}",
            "category": self._category(parser.title),
            "title": parser.title,
            "start_date": dates[0],
            "end_date": dates[1],
            "place": parser.fields.get("장소", "공식 페이지 확인"),
            "time": parser.fields.get("시간", "프로그램별 공식 안내 확인"),
            "fee": parser.fields.get("요금", "공식 페이지 확인"),
            "program": "상세 프로그램과 참여 방법은 서울시 공식 축제 페이지에서 확인",
            "official_url": url,
            "poster_url": poster_url,
        }

    def collect(self, recent_keys: list[str], count: int, *, today: date | None = None) -> list[dict]:
        if count < 1:
            raise ValueError("수집 개수는 1개 이상이어야 합니다.")
        checked = today or date.today()
        posts: list[dict] = []
        recent = set(recent_keys)
        for url in self.discover_urls()[:80]:
            code = re.search(r"festacode=(\d+)", url)
            topic_key = f"seoul-festival-{code.group(1)}" if code else ""
            if topic_key in recent:
                continue
            try:
                event = self.parse_event(url)
            except Exception:
                continue
            if date.fromisoformat(event["end_date"]) < checked:
                continue
            post = self._to_post(event, checked)
            posts.append(post)
            recent.add(post["topic_key"])
            if len(posts) == count:
                break
        return posts

    @staticmethod
    def _category(title: str) -> str:
        if any(term in title for term in ("마라톤", "러닝", "달리기")):
            return "러닝"
        if any(term in title for term in ("자전거", "사이클", "라이딩")):
            return "자전거"
        if any(term in title for term in ("캠핑", "레저")):
            return "캠핑·레저"
        return "행사·이벤트"

    @staticmethod
    def _to_post(event: dict, checked: date) -> dict:
        title = html.escape(event["title"])
        official_url = html.escape(event["official_url"], quote=True)
        summary = f"{event['place']}에서 열리는 {event['title']}의 공식 일정과 방문 정보를 정리했습니다."
        values = {key: html.escape(str(event[key])) for key in ("start_date", "end_date", "place", "time", "fee", "program")}
        content = f"""
<p>{html.escape(summary)}</p>
<p style="padding:18px;background:#f3faf5;border-left:4px solid #16a34a;"><strong>공식 안내</strong><br><a href="{official_url}" target="_blank" rel="noopener"><strong>서울시 공식 축제 페이지에서 최신 정보 확인하기 →</strong></a></p>
<h2>{title} 핵심 정보</h2>
<table data-ke-style="style12"><tbody>
<tr><td><strong>기간</strong></td><td>{values['start_date']} ~ {values['end_date']}</td></tr>
<tr><td><strong>장소</strong></td><td>{values['place']}</td></tr>
<tr><td><strong>운영 시간</strong></td><td>{values['time']}</td></tr>
<tr><td><strong>주요 프로그램</strong></td><td>{values['program']}</td></tr>
<tr><td><strong>관람료</strong></td><td>{values['fee']}</td></tr>
</tbody></table>
<h2>방문 전에 확인할 것</h2>
<ul><li>행사 당일 운영 여부와 프로그램 시간</li><li>사전 신청 또는 유료 관람 구역 여부</li><li>대중교통과 교통 통제 안내</li><li>우천·기상 상황에 따른 변경 공지</li></ul>
<h2>참고 및 공식 안내</h2><p><a href="{official_url}" target="_blank" rel="noopener">서울시 공식 축제 안내 바로가기</a></p>
<p><small>정보 확인일: {checked:%Y.%m.%d}. 일정과 운영 내용은 변경될 수 있으므로 방문 직전에 공식 페이지를 다시 확인하세요.</small></p>
""".strip()
        simple_title = re.sub(r"\s+", " ", event["title"]).strip()
        return {
            "topic_key": event["topic_key"],
            "category": event["category"],
            "title": f"{simple_title} 일정·장소·방문 안내",
            "summary": summary,
            "content_html": content,
            "tags": [simple_title, "서울축제", "서울행사", event["category"]],
            "sources": [{"title": "서울시 공식 축제 안내", "url": event["official_url"]}],
            "poster_url": event["poster_url"],
        }


def download_official_poster(post: dict, asset_dir: Path) -> Path:
    """Download the official poster, rejecting non-image or oversized responses."""
    request = Request(
        post["poster_url"],
        headers={"User-Agent": "ActiveLog/0.1 (+local content tool)"},
    )
    with urlopen(request, timeout=20) as response:
        content_type = response.headers.get_content_type()
        if content_type not in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
            raise RuntimeError("공식 포스터 응답이 이미지 형식이 아닙니다.")
        data = response.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise RuntimeError("공식 포스터 파일이 10MB를 초과합니다.")
    extension = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }[content_type]
    asset_dir.mkdir(parents=True, exist_ok=True)
    path = asset_dir / f"{post['topic_key']}{extension}"
    path.write_bytes(data)
    return path
