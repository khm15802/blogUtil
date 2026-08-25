from active_log.local_generator import LocalPostGenerator


def test_local_generator_creates_reviewable_post_without_api():
    post = LocalPostGenerator().generate("러닝", [])
    assert post["category"] == "러닝"
    assert post["sources"]
    assert "공식 안내" in post["content_html"]
    assert post["topic_key"] == "kim-dae-jung-peace-marathon-2026"
    assert "참가비·관람료" in post["content_html"]


def test_local_generator_avoids_same_day_key_collision():
    generator = LocalPostGenerator()
    first = generator.generate("자전거", [])
    second = generator.generate("자전거", [first["topic_key"]])
    assert first["topic_key"] != second["topic_key"]


def test_national_generation_still_creates_participation_event():
    post = LocalPostGenerator().generate("캠핑·레저", [], "national")
    assert post["category"] in {"러닝", "행사·이벤트"}
    assert post["sources"]


def test_generator_stops_instead_of_repeating_general_advice():
    recent = [event["slug"] + "-20260825" for event in __import__("active_log.local_generator", fromlist=["EVENTS"]).EVENTS]
    try:
        LocalPostGenerator().generate("러닝", recent)
    except RuntimeError as exc:
        assert "일반 정보 글" in str(exc)
    else:
        raise AssertionError("확인된 새 행사가 없으면 생성을 중단해야 합니다")
