from __future__ import annotations

from datetime import date


EVENTS = [
    {
        "region": "metro", "category": "러닝", "slug": "kim-dae-jung-peace-marathon-2026",
        "title": "제11회 2026 김대중 평화 마라톤 참가 신청 정보",
        "summary": "2026년 9월 6일 서울에서 열리는 김대중 평화 마라톤의 종목, 참가비와 공식 신청 정보를 정리했습니다.",
        "date": "2026년 9월 6일(일)", "place": "서울", "registration": "공식 홈페이지에서 신청",
        "program": "하프·10km·5km", "fee": "하프 40,000원 / 10km 40,000원 / 5km 35,000원",
        "official_url": "https://kdjrun.kr/info/", "apply_url": "https://kdjrun.kr/join/",
        "note": "모집 마감과 행사장 세부 위치는 신청 전 공식 공지에서 다시 확인하세요.",
        "tags": ["김대중평화마라톤", "서울마라톤", "2026마라톤", "마라톤접수"],
    },
    {
        "region": "metro", "category": "러닝", "slug": "masters-half-marathon-2026",
        "title": "2026 마스터즈 하프 마라톤 일정·종목·접수 안내",
        "summary": "상암 월드컵공원에서 열리는 2026 마스터즈 하프 마라톤의 참가 종목과 접수 일정을 안내합니다.",
        "date": "2026년 10월 3일(토) 오전 8시", "place": "서울 상암 월드컵공원 평화광장",
        "registration": "2026년 9월 21일까지 예정", "program": "하프·10km·5km",
        "fee": "각 종목 50,000원", "official_url": "https://mastershalf.kr/", "apply_url": "https://mastershalf.kr/",
        "note": "조기 마감될 수 있으므로 현재 접수 상태와 참가자 유의사항을 공식 홈페이지에서 확인하세요.",
        "tags": ["마스터즈하프마라톤", "서울러닝대회", "상암마라톤", "마라톤접수"],
    },
    {
        "region": "metro", "category": "행사·이벤트", "slug": "jongno-k-festival-2026",
        "title": "2026 종로K축제 기간·장소·참여 정보",
        "summary": "광화문광장에서 열리는 종로K축제의 축제 기간과 주요 프로그램, 방문 전 확인할 정보를 정리했습니다.",
        "date": "2026년 9월 10일~9월 19일 예정", "place": "서울 광화문광장",
        "registration": "일반 관람 중심·개별 프로그램 사전 신청 여부 확인", "program": "한복·한식·한글·국악·공예 등 우리문화 프로그램",
        "fee": "프로그램별 공식 안내 확인", "official_url": "https://festival.seoul.go.kr/festival/main/festivalView.do?festacode=655",
        "apply_url": "https://festival.seoul.go.kr/festival/main/festivalView.do?festacode=655",
        "note": "세부 프로그램과 운영 시간은 확정 공지가 올라오면 다시 확인하세요.",
        "tags": ["종로K축제", "광화문축제", "서울축제", "2026서울행사"],
    },
]


class LocalPostGenerator:
    """Create participation-information drafts from verified event records only."""

    def generate(self, category: str, recent_keys: list[str], region: str = "metro") -> dict:
        del category
        candidates = [event for event in EVENTS if region != "metro" or event["region"] == "metro"]
        event = next((item for item in candidates if not any(key.startswith(item["slug"]) for key in recent_keys)), None)
        if event is None:
            raise RuntimeError("새로 확인된 참여 행사 정보가 없습니다. 일반 정보 글은 대신 생성하지 않습니다.")

        checked = date.today()
        content = f"""
<p><strong>{event['title']}</strong>입니다. 참가하거나 방문할 독자가 바로 확인할 수 있도록 핵심 정보를 정리했습니다.</p>
<p style="padding:18px;background:#f3faf5;border-left:4px solid #16a34a;"><strong>신청·공식 안내</strong><br>{event['registration']}<br><a href="{event['apply_url']}" target="_blank" rel="noopener"><strong>공식 페이지에서 확인하기 →</strong></a></p>
<h2>행사 핵심 정보</h2>
<table data-ke-style="style12"><tbody>
<tr><td><strong>일정</strong></td><td>{event['date']}</td></tr>
<tr><td><strong>장소</strong></td><td>{event['place']}</td></tr>
<tr><td><strong>종목·프로그램</strong></td><td>{event['program']}</td></tr>
<tr><td><strong>참가비·관람료</strong></td><td>{event['fee']}</td></tr>
<tr><td><strong>접수 상태</strong></td><td>{event['registration']}</td></tr>
</tbody></table>
<h2>참가 전에 확인할 것</h2><p>{event['note']}</p>
<ul><li>최신 접수 상태와 마감 여부</li><li>집결 또는 입장 시간</li><li>주차·대중교통과 교통 통제</li><li>우천 시 변경·취소 공지</li><li>준비물과 참가자 유의사항</li></ul>
<h2>공식 안내</h2><p><a href="{event['official_url']}" target="_blank" rel="noopener">주최 측 공식 안내 바로가기</a></p>
<p><small>정보 확인일: {checked:%Y.%m.%d}. 일정과 접수 상태는 변경될 수 있으므로 신청 직전에 공식 페이지를 다시 확인하세요.</small></p>
""".strip()
        return {
            "topic_key": event["slug"], "category": event["category"],
            "title": event["title"], "summary": event["summary"], "content_html": content,
            "tags": event["tags"], "sources": [event["official_url"], event["apply_url"]],
        }
