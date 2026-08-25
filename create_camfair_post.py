from pathlib import Path

from active_log.db import Database


POST = {
    "topic_key": "event-camfair-gyeongnam-2026",
    "category": "캠핑·레저",
    "title": "2026 캠페어 경남 일정·장소·사전등록과 관람 팁",
    "summary": "9월 11일부터 창원컨벤션센터에서 열리는 캠핑&레저차량박람회의 일정, 사전등록, 입장과 관람 정보를 정리했습니다.",
    "tags": ["캠페어경남", "2026캠핑박람회", "창원캠핑", "캠핑카박람회", "캠핑용품"],
    "sources": [
        "https://www.camfair.kr/",
        "https://www.camfair.kr/board/?id=sub12",
        "https://www.camfair.kr/board/?c1=1&id=sub33",
    ],
    "content_html": """
<p>가을 캠핑을 앞두고 장비를 직접 비교해 보고 싶다면 <strong>2026 캠페어 경남</strong>을 살펴볼 만합니다. 텐트와 차박용품부터 캠핑카·카라반까지 한자리에서 볼 수 있어, 온라인 사진만으로 결정하기 어려웠던 장비를 확인하기 좋습니다.</p>
<p style="padding:18px;background:#f3faf5;border-left:4px solid #16a34a;"><strong>온라인 사전등록 안내</strong><br>사전등록은 본인 기준 1인 1매이며, 등록 시기에 따라 할인 입장이 적용됩니다. 동행인도 각각 등록해야 합니다.<br><a href="https://www.camfair.kr/board/?c1=1&amp;id=sub33" target="_blank" rel="noopener"><strong>캠페어 공식 사전등록 →</strong></a></p>
<h2>행사 핵심 정보</h2>
<table data-ke-style="style12"><tbody>
<tr><td><strong>행사명</strong></td><td>2026 캠페어 경남</td></tr>
<tr><td><strong>기간</strong></td><td>2026년 9월 11일(금)~13일(일)</td></tr>
<tr><td><strong>시간</strong></td><td>10:00~18:00, 입장 마감 17:30</td></tr>
<tr><td><strong>장소</strong></td><td>창원컨벤션센터(CECO) 제2전시장</td></tr>
<tr><td><strong>규모</strong></td><td>약 200부스, 관람객 1만 명 이상 예상</td></tr>
<tr><td><strong>문의</strong></td><td>캠페어 사무국 070-4866-1947</td></tr>
</tbody></table>
<h2>무엇을 볼 수 있나요?</h2>
<p>전시 품목은 캠핑카·트레일러·카라반 같은 레저차량, 텐트와 차박용품, 피크닉 용품, 차량용 장비, 아웃도어 의류와 감성 소품, 캠핑 먹거리까지 폭이 넓습니다. 캠핑장 예약 서비스와 지역 관광 홍보 부스도 만날 수 있습니다.</p>
<ul><li>캠핑카·카라반의 실내 높이와 수납공간 직접 확인</li><li>텐트 설치 크기와 패킹 부피 비교</li><li>의자·테이블은 직접 앉아 높이와 흔들림 확인</li><li>전기용품은 소비전력과 안전인증 확인</li><li>현장 할인 전 온라인 최저가와 사후지원 조건 비교</li></ul>
<h2>초보자는 이 순서로 둘러보세요</h2>
<p>입장하자마자 구매하기보다 먼저 전시장을 한 바퀴 돌며 관심 제품과 부스 번호를 메모하세요. 두 번째 동선에서 가격, 구성품, 배송비, 교환·수리 조건을 비교하면 충동구매를 줄일 수 있습니다. 캠핑카와 대형 텐트는 대기 줄이 생길 수 있어 오전에 먼저 보는 편이 낫습니다.</p>
<h2>입장 전에 알아둘 점</h2>
<p>공식 안내에 따르면 박람회 관람료는 행사에 따라 5천~1만원 수준이며 사전등록 기간에 따라 할인됩니다. 미성년자와 국가유공자, 장애인 본인은 증빙자료를 제시하면 별도 사전등록 없이 무료입장이 가능하다고 안내되어 있습니다. 정확한 경남 행사 입장료는 방문 전 관람 안내에서 다시 확인하세요.</p>
<h2>주차와 준비물</h2>
<p>주말에는 전시장 주변이 붐빌 수 있으므로 창원컨벤션센터 주차요금과 만차 시 대체 주차장을 미리 확인하세요. 스마트폰, 보조배터리, 줄자, 메모장 정도만 챙겨도 제품 크기와 가격을 비교하기 편합니다. 큰 제품을 구매한다면 차량 적재 공간도 미리 재두는 것이 좋습니다.</p>
<p><small>2026년 8월 23일 캠페어 공식 홈페이지 확인 기준입니다. 참가업체, 부스배치도, 입장료와 이벤트는 변경될 수 있으므로 방문 직전 공식 공지를 확인하세요.</small></p>
""".strip(),
}


def main() -> None:
    db = Database(Path("data/active_log.db"))
    if POST["topic_key"] in set(db.recent_topic_keys(500)):
        print("already exists")
        return
    post_id = db.save_post(POST)
    print(post_id)


if __name__ == "__main__":
    main()
