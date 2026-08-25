from .models import EventInfo, ImageAsset, PostData, SectionData, SeoData


def running_schedule_sample() -> PostData:
    images = [
        ImageAsset(slot="hero", filename="01_대표_도심_러닝.png", alt="도심을 달리는 러너들", position="hero"),
        ImageAsset(slot="september", filename="02_9월_강변_러닝.png", alt="초가을 강변 러닝", position="september"),
        ImageAsset(slot="closing", filename="03_9월_해질녘_러닝.png", alt="해 질 녘 달리는 러너", position="closing"),
        ImageAsset(slot="october", filename="04_10월_가을_호수_러닝.png", alt="가을 풍경 속 러닝", position="october"),
        ImageAsset(slot="november", filename="05_러닝_클로즈업.png", alt="러닝 대회를 준비하는 러너", position="november"),
    ]
    return PostData(
        title="2026 하반기 전국 러닝 대회 일정 총정리",
        category="러닝",
        subcategory="러닝 대회",
        date="2026.06.21",
        views_text="조회수 0",
        intro=(
            "가을은 기록을 노리는 러너와 첫 대회에 도전하는 입문자 모두에게 좋은 시즌입니다. "
            "9월부터 11월까지 참가 계획을 세울 때 살펴볼 대표 일정과 선택 기준을 한눈에 정리했습니다."
        ),
        notice=(
            "대회 일정, 접수 기간, 코스와 장소는 주최 측 사정에 따라 바뀔 수 있습니다. "
            "신청과 이동 계획을 확정하기 전에 반드시 각 대회의 공식 안내를 다시 확인하세요."
        ),
        images=images,
        sections=[
            SectionData(
                id="september", title="9월 추천 대회", image_slot="september",
                lead="늦더위와 높은 습도를 고려해 무리한 기록 도전보다 시즌 적응에 초점을 맞추기 좋은 달입니다.",
                events=[
                    EventInfo(name="JUST RUN10 세종", date="2026년 9월 5일(토)", location="세종마루공원 일원 금강변 인근", distances="5km / 10km", description="가볍게 5km 또는 10km에 도전하고 싶은 러너라면 관심을 가져볼 만한 대회입니다."),
                    EventInfo(name="강화해변마라톤", date="2026년 9월 13일(일)", location="강화 함상공원", distances="하프 / 10km / 5km / 커플런 / 가족런", description="하프부터 5km까지 다양한 종목이 준비되어 있어 러닝 경험에 따라 선택하기 좋습니다."),
                    EventInfo(name="인천송도국제마라톤대회", date="2026년 9월 20일(일)", location="국립 인천대학교 송도캠퍼스", distances="하프 / 10km / 5km", description="가을의 송도를 달리는 대표적인 러닝 대회 중 하나입니다."),
                ],
            ),
            SectionData(
                id="october", title="10월은 본격적인 PB 시즌", image_slot="october",
                lead="10월은 기온이 안정되면서 본격적으로 개인 기록(PB)에 도전하기 좋은 시기입니다.",
                paragraphs=["10월부터는 전국적으로 대회가 더욱 많아집니다. 목표 기록과 이동 거리, 코스 고저차를 함께 비교하고 최소 2~3주의 회복 기간을 고려해 일정을 선택하세요."],
                events=[EventInfo(name="조선일보 춘천마라톤", date="2026년 10월 25일(일)", location="춘천", distances="FULL / 10K", description="가을을 대표하는 장거리 레이스로, 춘천의 풍경과 함께 기록에 도전해볼 수 있는 대회입니다.")],
            ),
            SectionData(
                id="november", title="11월 대표 대회", image_slot="november",
                lead="쌀쌀한 날씨에 대비한 체온 관리와 출발 전 보온이 중요합니다.",
                events=[
                    EventInfo(name="2026 JTBC 서울마라톤", date="2026년 11월 1일", location="서울", distances="풀·10km", registration="접수 상태 공식 홈페이지 확인", description="도심 코스에서 열리는 하반기 대표 규모의 러닝 행사입니다."),
                    EventInfo(name="2026 김천 전국마라톤 대회", date="2026년 11월 1일", location="경북 김천", distances="하프·10km·5km", description="여러 거리 중 자신의 수준에 맞춰 선택할 수 있습니다."),
                ],
            ),
            SectionData(
                id="schedule", title="주요 대회 일정표",
                paragraphs=["아래 일정은 게시일 기준 참고용입니다. 접수 전 공식 공지를 확인하세요."],
            ),
            SectionData(
                id="choice", title="어떤 대회를 선택하면 좋을까", variant="tips",
                bullets=[
                    "첫 대회라면 이동이 편하고 제한 시간이 넉넉한 5km 또는 10km를 선택하세요.",
                    "기록이 목표라면 코스 고저차, 출발 인원, 급수대 간격을 함께 확인하세요.",
                    "여행을 겸한다면 숙소와 대중교통을 접수 전에 먼저 확보하세요.",
                ],
            ),
            SectionData(
                id="checklist", title="대회 참가 전 체크리스트", variant="checklist",
                bullets=["접수 완료 문자와 참가 번호 확인", "신분증·기록칩·배번호 준비", "대회 당일 교통 통제 확인", "검증된 러닝화와 복장 사용", "기온에 맞는 수분·보온 계획 준비"],
            ),
            SectionData(
                id="closing", title="마무리", image_slot="closing",
                paragraphs=["좋은 대회 선택은 목표와 현재 훈련량을 정확히 아는 것에서 시작합니다. 일정이 확정되면 역산해 훈련 계획을 세우고, 무리 없이 출발선에 서는 것을 첫 번째 목표로 삼아보세요."],
            ),
        ],
        hashtags=["2026마라톤", "러닝대회", "전국마라톤일정", "가을마라톤", "10km대회", "하프마라톤"],
        seo=SeoData(
            description="2026년 9월부터 11월까지 전국 주요 러닝·마라톤 대회 일정과 참가 전 선택 기준 및 체크리스트를 정리합니다.",
            keywords=["2026 러닝 대회", "2026 마라톤 일정", "가을 마라톤", "전국 러닝 대회"],
        ),
    )
