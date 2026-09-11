from __future__ import annotations

import html
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


CATEGORIES = ["러닝", "자전거", "캠핑·레저", "행사·이벤트"]
DAILY_CATEGORIES = ("러닝", "자전거", "캠핑·레저")
SEOUL_FESTIVAL_MAIN_URL = "https://festival.seoul.go.kr/festival/main/festivalMain.do"
SEOUL_FESTIVAL_BASE_URL = "https://festival.seoul.go.kr"
KAAF_SCHEDULE_URL = "https://www.kaaf.or.kr/ver3/info/internal.asp?currentYear=2026"
GOCAF_URL = "https://gocaf.kr/"
GOCAF_KINTEX_FINAL_PART1_URL = (
    "https://gocaf.kr/exhibition-info/2026-gocaf-kintex-the-final-season1/"
)
GOCAF_KINTEX_FINAL_PART1_POSTER_URL = (
    "https://d1lfwrrxe5dvss.cloudfront.net/wp-content/uploads/2026/06/23225452/"
    "8.-261009_%EA%B3%A0%EC%B9%B4%ED%94%84-%ED%82%A8%ED%85%8D%EC%8A%A4_"
    "%EA%B5%AD%EB%AC%B8_%EC%9B%B9%EC%9A%A9%ED%8F%AC%EC%8A%A4%ED%84%B0_"
    "x336x504px.png"
)
GOCAF_KINTEX_FINAL_PART2_URL = (
    "https://gocaf.kr/exhibition-info/2026-gocaf-kintex-the-final-season2/"
)
GOCAF_KINTEX_FINAL_PART2_POSTER_URL = (
    "https://d1lfwrrxe5dvss.cloudfront.net/wp-content/uploads/2026/09/02000907/"
    "10.-261127_%EA%B3%A0%EC%B9%B4%ED%94%84-%ED%82%A8%ED%85%8D%EC%8A%A4_"
    "%EA%B5%AD%EB%AC%B8_%EC%9B%B9%EC%9A%A9%ED%8F%AC%EC%8A%A4%ED%84%B0_"
    "336x504px.png"
)

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
    # 대회 공식 안내와 포스터를 2026-09-09 대조한 전국 대회.
    {
        "topic_key": "teddy-circuit-run-inje-2026", "category": "러닝",
        "title": "2026 인제베어 테디서킷런",
        "summary": "인제 스피디움에서 열리는 5K·10K 서킷 러닝 대회입니다.",
        "start_date": "2026-10-05", "end_date": "2026-10-05",
        "place": "강원 인제 스피디움", "time": "10K 11:00 / 5K 11:30 출발",
        "fee": "65,000원 (신청 가능 여부와 부문별 조건은 공식 안내 확인)",
        "program": "5K·10K 서킷 러닝, 완주 메달, 기록 측정 및 행사 부스",
        "official_url": "https://teddymarathon.com/",
        "poster_url": "https://teddymarathon.com/assets/images/poster-full.jpg",
        "source_label": "테디서킷런 공식 대회 안내", "tags": ["인제", "서킷런", "러닝"],
    },
    {
        "topic_key": "chuncheon-marathon-2026", "category": "러닝",
        "title": "2026 조선일보 춘천마라톤",
        "summary": "춘천 공지천교에서 출발하는 풀코스·10km 마라톤입니다.",
        "start_date": "2026-10-25", "end_date": "2026-10-25",
        "place": "강원 춘천 공지천교 (집결: 공지천 인조잔디구장)", "time": "09:00 출발",
        "fee": "풀코스 150,000원 / 10km 100,000원 (접수 상태는 공식 안내 확인)",
        "program": "풀코스 42.195km 및 10km, 풀코스 제한 시간 5시간 30분·10km 1시간 30분",
        "official_url": "https://www.chuncheonmarathon.com/rally/info.html",
        "poster_url": "https://image.chosun.com/chuncheonmarathon/2026/main-img2.png",
        "source_label": "춘천마라톤 공식 대회 요강", "tags": ["춘천", "마라톤", "러닝"],
    },
    {
        "topic_key": "binggrae-granfondo-2026", "category": "자전거",
        "title": "2026 빙그레 그란폰도",
        "summary": "공주시민운동장에서 출발하는 그란폰도·메디오폰도입니다.",
        "start_date": "2026-10-09", "end_date": "2026-10-09",
        "place": "충남 공주시민운동장", "time": "08:00~14:30",
        "fee": "50,000원 (접수 상태는 공식 안내 확인)",
        "program": "그란폰도 113km·메디오폰도 106km. 악천후 시 10월 24일 순연 예정으로 공식 공지 확인 필요",
        "official_url": "https://www.binggraegranfondo.com/sub/event.html",
        "poster_url": quote("https://www.binggraegranfondo.com/_wp/data/banner/main-visual/20260827104313_1_빙그레-키비-3-2.png", safe=":/"),
        "source_label": "빙그레 그란폰도 공식 행사 안내", "tags": ["공주", "그란폰도", "자전거"],
    },
    {
        "topic_key": "tongyeong-granfondo-2026", "category": "자전거",
        "title": "2026 통영 그란폰도",
        "summary": "통영 트라이애슬론 광장에서 출발하는 그란폰도입니다.",
        "start_date": "2026-10-17", "end_date": "2026-10-17",
        "place": "경남 통영시 트라이애슬론 광장", "time": "08:00 출발",
        "fee": "70,000원 (접수 상태는 공식 안내 확인)",
        "program": "그란폰도 96.9km, 통영 해안 및 산양읍 일대 코스",
        "official_url": "https://www.tongyeongfondo.com/about/about",
        "poster_url": "https://www.tongyeongfondo.com/img/poster_img-fd0b393080d681c9a446c7c7a3fde40d.png",
        "source_label": "통영 그란폰도 공식 대회 소개", "tags": ["통영", "그란폰도", "자전거"],
    },
    {
        "topic_key": "kaaf-national-university-athletics-2026",
        "category": "러닝",
        "title": "제80회 전국대학대항육상경기대회",
        "summary": "대한육상연맹 공식 국내경기 일정에 등록된 전국 대학 육상대회입니다.",
        "start_date": "2026-09-14", "end_date": "2026-09-16", "place": "공식 일정 확인",
        "time": "세부 경기 시간은 공식 요강 확인", "fee": "공식 요강 확인",
        "program": "트랙·필드 종목 경기", "official_url": KAAF_SCHEDULE_URL,
        "poster_url": "", "tags": ["육상대회", "러닝", "2026전국대회"],
    },
    {
        "topic_key": "kaaf-danyang-moonlight-2026",
        "category": "러닝",
        "title": "2026 단양 달빛 중장거리 챌린지대회",
        "summary": "대한육상연맹 공식 일정에 등록된 단양 중장거리 육상 챌린지대회입니다.",
        "start_date": "2026-10-03", "end_date": "2026-10-03", "place": "단양",
        "time": "세부 경기 시간은 공식 요강 확인", "fee": "공식 요강 확인",
        "program": "중장거리 달리기 경기", "official_url": KAAF_SCHEDULE_URL,
        "poster_url": "", "tags": ["단양달빛챌린지", "러닝", "2026육상대회"],
    },
    {
        "topic_key": "kaaf-national-sports-festival-2026",
        "category": "러닝",
        "title": "제107회 전국체육대회 육상경기",
        "summary": "대한육상연맹 공식 국내경기 일정에 등록된 전국체육대회 육상경기입니다.",
        "start_date": "2026-10-18", "end_date": "2026-10-21", "place": "서귀포",
        "time": "세부 경기 시간은 공식 요강 확인", "fee": "공식 안내 확인",
        "program": "트랙·필드 종목 경기", "official_url": KAAF_SCHEDULE_URL,
        "poster_url": "", "tags": ["전국체전", "육상경기", "러닝", "2026전국체전"],
    },
    {
        "topic_key": "gocaf-kintex-final-2026",
        "category": "캠핑·레저",
        "title": "고카프 킨텍스 더 파이널 시즌 PART 1",
        "summary": "공식 고카프 안내에 공개된 캠핑·레포츠 박람회 일정입니다.",
        "start_date": "2026-10-09", "end_date": "2026-10-11", "place": "일산 킨텍스 2전시장",
        "time": "10:00~18:00", "fee": "입장료·할인은 공식 안내 확인",
        "program": "캠핑 장비 전시, 레포츠 체험, 캠프 푸드 페스타",
        "official_url": GOCAF_KINTEX_FINAL_PART1_URL,
        "poster_url": GOCAF_KINTEX_FINAL_PART1_POSTER_URL,
        "tags": ["고카프", "캠핑", "캠핑박람회", "2026캠핑행사"],
    },
    {
        "topic_key": "gocaf-kintex-final-part2-2026",
        "category": "캠핑·레저",
        "title": "고카프 킨텍스 더 파이널 시즌 PART 2",
        "summary": "공식 고카프 안내에 공개된 캠핑·레포츠 박람회 일정입니다.",
        "start_date": "2026-11-27", "end_date": "2026-11-29", "place": "일산 킨텍스 2전시장",
        "time": "10:00~18:00", "fee": "입장료·할인은 공식 안내 확인",
        "program": "캠핑 장비 전시, 레포츠 체험, 참가기업 신제품 소개",
        "official_url": GOCAF_KINTEX_FINAL_PART2_URL,
        "poster_url": GOCAF_KINTEX_FINAL_PART2_POSTER_URL,
        "tags": ["고카프", "캠핑", "캠핑박람회", "2026캠핑행사"],
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
                and item.get("poster_url")
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
<table class="activelog-info-table" data-ke-style="style12" style="width:100%;border-collapse:collapse;color:#222;background:#fff"><tbody>
<tr><td><strong>기간</strong></td><td><span style="color:#222 !important">{escaped['start_date']} ~ {escaped['end_date']}</span></td></tr>
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
        def field(*names: str, default: str = "") -> str:
            return next((parser.fields[name] for name in names if parser.fields.get(name)), default)

        return {
            "topic_key": f"seoul-festival-{match.group(1)}",
            "category": self._category(parser.title),
            "title": parser.title,
            "start_date": dates[0],
            "end_date": dates[1],
            "place": field("장소", default="공식 페이지 확인"),
            "time": field("시간", "운영시간", default="프로그램별 공식 안내 확인"),
            "fee": field("요금", "이용요금", "입장료", default="공식 페이지 확인"),
            "program": field(
                "프로그램", "행사내용", "내용",
                default="상세 프로그램과 참여 방법은 서울시 공식 축제 페이지에서 확인",
            ),
            "homepage": field("홈페이지", "누리집"),
            "inquiry": field("문의", "문의전화", "전화번호"),
            "official_url": url,
            "poster_url": poster_url,
        }

    def collect(
        self,
        recent_keys: list[str],
        count: int,
        *,
        today: date | None = None,
        category: str | None = None,
    ) -> list[dict]:
        if count < 1:
            raise ValueError("수집 개수는 1개 이상이어야 합니다.")
        checked = today or date.today()
        posts: list[dict] = []
        recent = set(recent_keys)
        try:
            discovered_urls = self.discover_urls()[:80]
        except Exception:
            # 한 출처가 일시적으로 차단되어도 카테고리별 공식 보완 목록은 사용한다.
            discovered_urls = []
        for url in discovered_urls:
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
            if category and event["category"] != category:
                continue
            if not event.get("poster_url"):
                continue
            post = self._to_post(event, checked)
            posts.append(post)
            recent.add(post["topic_key"])
            if len(posts) == count:
                break
        # 보완 목록: 연맹·주최사 공식 일정이 별도 페이지에 공개된 종목도
        # 동일한 검증 템플릿으로 제공한다. 서울 축제 수집 결과가 부족할 때만 사용한다.
        if len(posts) < count and (category is None or category in {"러닝", "자전거", "캠핑·레저"}):
            for event in OFFICIAL_EVENTS:
                if not event.get("poster_url"):
                    continue
                if event["topic_key"] in recent or (category and event["category"] != category):
                    continue
                if date.fromisoformat(event["end_date"]) < checked:
                    continue
                posts.append(self._to_post(event, checked))
                recent.add(event["topic_key"])
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
        start = date.fromisoformat(event["start_date"])
        end = date.fromisoformat(event["end_date"])
        date_label = (
            f"{start.year}년 {start.month}월 {start.day}일"
            if start == end
            else f"{start.year}년 {start.month}월 {start.day}일부터 {end.month}월 {end.day}일까지"
        )
        summary = f"{event['title']}은(는) {date_label} {event['place']}에서 열립니다. 운영 시간, 요금과 방문 전 확인사항을 공식 자료 기준으로 정리했습니다."
        values = {key: html.escape(str(event[key])) for key in ("start_date", "end_date", "place", "time", "fee", "program")}
        homepage = html.escape(str(event.get("homepage", "")), quote=True)
        inquiry = html.escape(str(event.get("inquiry", "")))
        participation_rows = []
        fee_label = "참가비" if event["category"] in {"러닝", "자전거"} else "관람료"
        if event.get("homepage"):
            participation_rows.append(f'<li><strong>행사 홈페이지:</strong> {homepage}</li>')
        if event.get("inquiry"):
            participation_rows.append(f"<li><strong>문의:</strong> {inquiry}</li>")
        participation_rows.append(f"<li><strong>{fee_label}:</strong> {values['fee']}</li>")
        participation_html = "".join(participation_rows)
        source_label = html.escape(event.get("source_label", "공식 일정 페이지"))
        if "kaaf.or.kr" in event["official_url"]:
            source_label = "대한육상연맹 공식 경기 일정"
        elif "gocaf.kr" in event["official_url"]:
            source_label = "고카프 공식 행사 안내"
        content = f"""
<p><strong>{title}</strong> 방문을 계획한다면 날짜와 운영 시간을 먼저 확인하세요. {html.escape(summary)}</p>
<p style="padding:18px;background:#f3faf5;border-left:4px solid #16a34a;"><strong>공식 안내</strong><br><a href="{official_url}" target="_blank" rel="noopener"><strong>{source_label}에서 최신 정보 확인하기 →</strong></a></p>
<h2>{title} 핵심 정보</h2>
<table class="activelog-info-table" data-ke-style="style12" style="width:100%;border-collapse:collapse;color:#222;background:#fff"><tbody>
<tr><td><strong>기간</strong></td><td><span style="color:#222 !important">{values['start_date']} ~ {values['end_date']}</span></td></tr>
<tr><td><strong>장소</strong></td><td>{values['place']}</td></tr>
<tr><td><strong>운영 시간</strong></td><td>{values['time']}</td></tr>
<tr><td><strong>주요 프로그램</strong></td><td>{values['program']}</td></tr>
<tr><td><strong>{fee_label}</strong></td><td>{values['fee']}</td></tr>
</tbody></table>
<h2>언제 어디서 열리나</h2>
<p>행사 기간은 <strong>{values['start_date']}부터 {values['end_date']}까지</strong>이며 장소는 <strong>{values['place']}</strong>입니다. 공식 안내에 표시된 운영 시간은 <strong>{values['time']}</strong>입니다. 날짜별 프로그램이 다를 수 있으므로 방문할 날짜의 세부 시간표를 다시 확인하는 것이 좋습니다.</p>
<h2>프로그램과 참여 정보</h2>
<p>{values['program']}</p><ul>{participation_html}</ul>
<h2>{values['place']} 방문 전 확인사항</h2>
<ul><li>행사 당일 운영 여부와 회차별 시작 시간</li><li>사전 신청 또는 유료 구역 운영 여부</li><li>행사장과 가까운 대중교통 및 당일 교통 통제</li><li>우천·기상 상황에 따른 변경 또는 취소 공지</li></ul>
<h2>참고 및 공식 안내</h2><p><a href="{official_url}" target="_blank" rel="noopener">{source_label} 바로가기</a></p>
<p><small>정보 확인일: {checked:%Y.%m.%d}. 일정과 운영 내용은 변경될 수 있으므로 방문 직전에 공식 페이지를 다시 확인하세요.</small></p>
""".strip()
        simple_title = re.sub(r"\s+", " ", event["title"]).strip()
        year = str(start.year)
        seo_title = f"{simple_title} {year} 일정·시간·장소·요금"
        if year in simple_title:
            seo_title = f"{simple_title} 일정·시간·장소·요금"
        place_tags = [
            token for token in re.split(r"[\s,·/]+", str(event["place"]))
            if 2 <= len(token) <= 12 and token not in {"서울", "일대", "등"}
        ][:2]
        tag_title = re.sub(rf"^{re.escape(year)}\s*", "", simple_title)
        tags = list(dict.fromkeys([
            simple_title, f"{year}{re.sub(r'[^0-9A-Za-z가-힣]', '', tag_title)}",
            *place_tags, *event.get("tags", []), event["category"],
        ]))[:8]
        return {
            "topic_key": event["topic_key"],
            "category": event["category"],
            "title": seo_title,
            "summary": summary,
            "content_html": content,
            "tags": tags,
            "sources": [{"title": source_label, "url": event["official_url"]}],
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
