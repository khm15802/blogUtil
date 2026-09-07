import asyncio

from active_log.publisher import TistoryPublisher


def test_clear_editor_content_uses_tinymce_when_available():
    class Page:
        def __init__(self):
            self.script = ""

        async def wait_for_timeout(self, _milliseconds):
            return None

        async def evaluate(self, script):
            self.script = script
            return True

    page = Page()
    asyncio.run(TistoryPublisher._clear_editor_content(page))
    assert "setContent('')" in page.script


def test_set_and_verify_title_accepts_matching_live_value():
    class TitleInput:
        def __init__(self):
            self.value = ""

        async def fill(self, value):
            self.value = value

        async def press(self, key):
            assert key == "Tab"

        async def input_value(self):
            return self.value

    title_input = TitleInput()
    asyncio.run(TistoryPublisher._set_and_verify_title(title_input, "새 행사"))
    assert title_input.value == "새 행사"


def test_set_and_verify_title_rejects_restored_autosave_title():
    class RestoredTitleInput:
        async def fill(self, _value):
            return None

        async def press(self, _key):
            return None

        async def input_value(self):
            return "이전 글"

    try:
        asyncio.run(
            TistoryPublisher._set_and_verify_title(RestoredTitleInput(), "새 행사")
        )
    except RuntimeError as exc:
        assert "제목이 다른 글로 바뀌어" in str(exc)
    else:
        raise AssertionError("다른 제목은 게시 전에 차단되어야 합니다.")


def test_fetch_view_counts_normalizes_tistory_statistics():
    class Page:
        def __init__(self):
            self.script = ""
            self.post_ids = []

        async def evaluate(self, script, post_ids):
            self.script = script
            self.post_ids = post_ids
            return {"30": 7, "31": "12", "invalid": 99}

    page = Page()
    counts = asyncio.run(TistoryPublisher._fetch_view_counts(page, [30, 31]))

    assert counts == {30: 7, 31: 12}
    assert page.post_ids == [30, 31]
    assert "/manage/v2/statistics/entry/base" in page.script
    assert "Math.min(6" in page.script


def test_fetch_view_counts_skips_browser_call_for_empty_list():
    class Page:
        async def evaluate(self, *_args):
            raise AssertionError("빈 목록에서는 브라우저를 호출하면 안 됩니다.")

    assert asyncio.run(TistoryPublisher._fetch_view_counts(Page(), [])) == {}
