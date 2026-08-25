from pathlib import Path

from active_log.quality import inspect_post


def _post(**updates):
    post = {
        "topic_key": "valid-topic-2026",
        "title": "게시 전 검사를 통과하는 충분한 제목",
        "summary": "독자에게 필요한 내용을 충분히 설명하는 게시글 요약입니다.",
        "content_html": "<p>본문입니다.</p>",
        "sources": ["https://example.com/official"],
    }
    post.update(updates)
    return post


def test_valid_post_has_no_issues(tmp_path: Path):
    assert inspect_post(_post(), tmp_path) == []


def test_invalid_source_and_topic_are_errors(tmp_path: Path):
    issues = inspect_post(_post(topic_key="잘못된 키", sources=["not-a-url"]), tmp_path)
    assert sum(issue.level == "error" for issue in issues) == 2


def test_external_image_is_warning_and_missing_local_image_is_error(tmp_path: Path):
    html = '<img src="https://example.com/a.jpg" alt="외부"><img src="assets/missing.png" alt="로컬">'
    issues = inspect_post(_post(content_html=html), tmp_path)
    assert any(issue.level == "warning" and "외부 주소" in issue.message for issue in issues)
    assert any(issue.level == "error" and "찾을 수 없습니다" in issue.message for issue in issues)


def test_source_objects_from_generator_are_supported(tmp_path: Path):
    issues = inspect_post(_post(sources=[{"title": "공식", "url": "https://example.com/official"}]), tmp_path)
    assert not any(issue.level == "error" for issue in issues)
