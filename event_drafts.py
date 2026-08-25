from pathlib import Path

from active_log.db import Database


POSTS = [
    {
        "topic_key": "event-cheorwon-dmz-marathon-2026",
        "category": "러닝",
        "title": "제23회 철원DMZ 국제평화마라톤 일정·장소·참가자 체크사항",
        "summary": "2026년 9월 5일 고석정에서 열리는 철원DMZ 국제평화마라톤의 핵심 일정과 참가 전 확인사항입니다.",
        "tags": ["철원DMZ마라톤", "2026마라톤", "철원여행", "러닝대회", "마라톤일정"],
        "sources": ["https://www.dmzrun.kr/"],
        "content_html": """
<p><strong>제23회 철원DMZ 국제평화마라톤</strong>이 2026년 9월 5일 토요일 철원 고석정 일원에서 열립니다. 접수를 마친 참가자라면 기록 욕심보다 집결 시간과 이동 동선을 먼저 확인할 시점입니다.</p>
<h2>대회 기본 정보</h2>
<table data-ke-style="style12"><tbody>
<tr><td><strong>대회일</strong></td><td>2026년 9월 5일(토)</td></tr>
<tr><td><strong>출발</strong></td><td>오전 9시</td></tr>
<tr><td><strong>장소</strong></td><td>강원특별자치도 철원군 고석정 일원</td></tr>
<tr><td><strong>종목</strong></td><td>풀·하프·10km·5km 걷기</td></tr>
<tr><td><strong>공식 홈페이지</strong></td><td><a href="https://www.dmzrun.kr/" target="_blank" rel="noopener">dmzrun.kr</a></td></tr>
</tbody></table>
<h2>지금 확인할 것</h2>
<p>대회가 가까워진 만큼 신규 접수 가능 여부보다 배번호와 기념품 배송, 종목 변경 공지, 주차 및 셔틀 안내를 확인하는 편이 중요합니다. 공식 홈페이지 공지사항을 기준으로 보고, 문자로 받은 안내가 있다면 함께 대조하세요.</p>
<ul><li>집결지까지의 예상 이동 시간</li><li>배번호와 기록칩 수령 여부</li><li>당일 교통 통제 및 주차 안내</li><li>철원 시간대별 기온·강수·바람</li><li>종목별 제한시간과 급수 위치</li></ul>
<h2>9월 초라도 더위 대비</h2>
<p>오전 출발이지만 햇빛과 습도에 따라 체감온도가 높을 수 있습니다. 평소 사용하던 러닝화와 복장으로 참가하고, 새로운 보충제나 장비를 대회 당일 처음 시험하지 않는 편이 좋습니다.</p>
<p><small>이 글은 2026년 8월 23일 공식 홈페이지 확인 내용을 기준으로 작성했습니다. 일정과 운영 방식은 변경될 수 있으니 출발 전 공식 공지를 다시 확인하세요.</small></p>
""".strip(),
    },
    {
        "topic_key": "event-gongju-baekje-marathon-2026",
        "category": "러닝",
        "title": "2026 공주백제마라톤 9월 20일 개최, 참가자 일정 총정리",
        "summary": "공주시민운동장에서 열리는 2026 공주백제마라톤의 집결·출발 시간과 종목별 준비사항을 정리했습니다.",
        "tags": ["공주백제마라톤", "2026마라톤", "공주마라톤", "마라톤일정", "러닝대회"],
        "sources": ["https://www.gongjumarathon.com/", "https://www.gongjumarathon.com/terms"],
        "content_html": """
<p>2026 공주백제마라톤은 9월 20일 일요일 오전 8시 공주시민운동장에서 출발합니다. 공식 포스터에는 풀코스, 32km, 하프, 10km 종목이 안내되어 있습니다.</p>
<h2>대회 기본 정보</h2>
<table data-ke-style="style12"><tbody>
<tr><td><strong>대회일</strong></td><td>2026년 9월 20일(일)</td></tr>
<tr><td><strong>집결</strong></td><td>오전 7시</td></tr>
<tr><td><strong>출발</strong></td><td>오전 8시</td></tr>
<tr><td><strong>장소</strong></td><td>공주시민운동장</td></tr>
<tr><td><strong>종목</strong></td><td>풀코스·32km·하프·10km</td></tr>
<tr><td><strong>공식 홈페이지</strong></td><td><a href="https://www.gongjumarathon.com/" target="_blank" rel="noopener">gongjumarathon.com</a></td></tr>
</tbody></table>
<h2>출발 그룹과 기록 측정</h2>
<p>공식 참가자 유의사항에 따르면 풀·32km·하프 참가자는 제출 기록을 바탕으로 배정된 그룹 순서로 출발하고, 이후 10km가 출발합니다. 기록은 출발 매트를 통과한 순간부터 측정하는 넷타임 방식입니다.</p>
<h2>종목별 제한시간</h2>
<ul><li>풀코스 5시간</li><li>32km 4시간</li><li>하프 2시간 30분</li><li>10km 1시간 30분</li></ul>
<p>제한시간 이후에는 교통 통제가 해제될 수 있으므로 운영요원의 안내를 따라야 합니다. 참가자는 배송 물품, 배번호, 셔틀버스 공지를 미리 확인하고 오전 7시 이전 도착을 기준으로 이동 계획을 세우는 편이 안전합니다.</p>
<p><small>2026년 8월 23일 공식 홈페이지 기준입니다. 접수는 이미 진행된 대회이므로 추가 접수 여부는 공지사항에서 확인하세요.</small></p>
""".strip(),
    },
    {
        "topic_key": "event-binggrae-granfondo-2026",
        "category": "자전거",
        "title": "2026 빙그레 그란폰도 일정과 코스, 참가 전 확인사항",
        "summary": "10월 9일 공주에서 열리는 빙그레 그란폰도의 코스 거리, 상승고도, 참가비와 순연 기준을 정리했습니다.",
        "tags": ["빙그레그란폰도", "2026그란폰도", "자전거대회", "공주라이딩", "그란폰도일정"],
        "sources": ["https://www.binggraegranfondo.com/sub/event.html"],
        "content_html": """
<p>2026 빙그레 그란폰도는 10월 9일 금요일 공주시민운동장을 출발하는 동호인 자전거 행사입니다. 공식 홈페이지에는 선착순 마감 안내가 게시되어 있어, 현재는 신규 접수보다 참가자용 준비 정보 확인이 필요한 시점입니다.</p>
<h2>행사 기본 정보</h2>
<table data-ke-style="style12"><tbody>
<tr><td><strong>일시</strong></td><td>2026년 10월 9일(금) 08:00~14:30</td></tr>
<tr><td><strong>장소</strong></td><td>공주시민운동장</td></tr>
<tr><td><strong>그란폰도</strong></td><td>113km / 누적 상승 1,342m</td></tr>
<tr><td><strong>메디오폰도</strong></td><td>106km / 누적 상승 907m</td></tr>
<tr><td><strong>참가비</strong></td><td>50,000원</td></tr>
<tr><td><strong>참가 규모</strong></td><td>선착순 2,000명</td></tr>
<tr><td><strong>공식 홈페이지</strong></td><td><a href="https://www.binggraegranfondo.com/sub/event.html" target="_blank" rel="noopener">행사안내 바로가기</a></td></tr>
</tbody></table>
<h2>악천후 시 순연일</h2>
<p>공식 안내에는 악천후 시 10월 24일로 순연될 예정이라고 적혀 있습니다. 비 예보가 있다면 개인 판단만으로 출발하지 말고 주최 측 공지를 기준으로 확인해야 합니다.</p>
<h2>참가자가 미리 볼 항목</h2>
<ul><li>공식 GPX를 기기에 넣고 코스 이탈 경고 확인</li><li>브레이크 패드·타이어·체인 상태 점검</li><li>보급 구간과 컷오프 위치 확인</li><li>전조등·후미등 충전</li><li>행사 당일 공주시 교통 통제와 주차 안내 확인</li></ul>
<p>두 코스 모두 100km가 넘기 때문에 평소 장거리 경험과 보급 계획이 필요합니다. 참가권 임의 양도는 공식 참가자로 인정되지 않는다는 안내도 있으므로 반드시 본인 신청 정보를 확인하세요.</p>
<p><small>2026년 8월 23일 공식 홈페이지 기준이며, 행사 세부 내용은 주최 측 사정에 따라 변경될 수 있습니다.</small></p>
""".strip(),
    },
    {
        "topic_key": "event-andong-maskdance-festival-2026",
        "category": "행사·이벤트",
        "title": "2026 안동국제탈춤페스티벌 일정·장소·개막식 안내",
        "summary": "9월 24일부터 10월 4일까지 열리는 안동국제탈춤페스티벌의 장소와 개막·폐막 주요 일정을 정리했습니다.",
        "tags": ["안동국제탈춤페스티벌", "안동축제", "2026축제", "가을축제", "경북여행"],
        "sources": ["https://www.maskdance.com/2024/main.asp", "https://www.maskdance.com/2024/sub2/sub0.asp"],
        "content_html": """
<p>2026 안동국제탈춤페스티벌이 9월 24일부터 10월 4일까지 11일간 열립니다. 올해 주제는 <strong>‘가면의 기억, 모두의 춤’</strong>입니다. 안동역 한 곳에서만 열리는 행사가 아니라 원도심, 탈춤공원, 하회마을까지 여러 공간에 프로그램이 나뉘어 있습니다.</p>
<h2>축제 기본 정보</h2>
<table data-ke-style="style12"><tbody>
<tr><td><strong>기간</strong></td><td>2026년 9월 24일(목)~10월 4일(일)</td></tr>
<tr><td><strong>전야제</strong></td><td>9월 24일 18:00~20:00</td></tr>
<tr><td><strong>개막식</strong></td><td>9월 25일 18:00~20:00</td></tr>
<tr><td><strong>폐막식</strong></td><td>10월 4일 20:30~</td></tr>
<tr><td><strong>장소</strong></td><td>중앙선 1942 안동역·탈춤공원·원도심·하회마을 등</td></tr>
<tr><td><strong>공식 홈페이지</strong></td><td><a href="https://www.maskdance.com/2024/main.asp" target="_blank" rel="noopener">maskdance.com</a></td></tr>
</tbody></table>
<h2>개막일에 볼 수 있는 것</h2>
<p>9월 25일 오후 5시 30분부터 원도심 일대에서 국내외 공연단과 시민이 참여하는 개막식 퍼레이드가 예정되어 있습니다. 이어 안동역 메인무대에서 개막 선언과 주제공연, 공연단 입장 세리머니가 진행됩니다. 마지막에는 대동난장과 불꽃놀이가 안내되어 있습니다.</p>
<h2>하루 동선은 장소 두 곳만</h2>
<p>행사장이 넓게 분산되어 있으므로 안동역·원도심을 한 묶음으로 보고, 하회마을은 별도 일정으로 잡는 편이 좋습니다. 보고 싶은 탈춤 공연 시간을 먼저 정한 뒤 식사와 이동 시간을 붙이세요. 야간 행사까지 본다면 귀가 교통편과 주차장 출차 동선도 미리 확인하는 것이 좋습니다.</p>
<p><small>2026년 8월 23일 공식 홈페이지 기준입니다. 공연별 시간표와 우천 변경 사항은 방문 직전 공식 일정표를 확인하세요.</small></p>
""".strip(),
    },
]


def main() -> None:
    db = Database(Path("data/active_log.db"))
    existing = set(db.recent_topic_keys(500))
    for post in POSTS:
        if post["topic_key"] in existing:
            print(f"skip: {post['title']}")
            continue
        post_id = db.save_post(post)
        print(f"created {post_id}: {post['title']}")


if __name__ == "__main__":
    main()
