from pathlib import Path

from active_log.quality import inspect_post


def _post(**updates):
    post = {
        "topic_key": "valid-topic-2026",
        "title": "게시 전 검사를 통과하는 충분한 제목",
        "summary": "독자에게 필요한 내용을 충분히 설명하는 게시글 요약입니다.",
        "content_html": (
            "<h2>행사 일정</h2><p>" + "공식 일정과 운영 정보를 자세히 확인했습니다. " * 20 + "</p>"
            "<h2>방문 정보</h2><p>대중교통과 운영 시간을 확인하세요.</p>"
            "<h2>공식 안내</h2><p>변경 사항은 공식 페이지에서 확인하세요.</p>"
        ),
        "tags": ["행사명", "2026서울행사", "서울광장"],
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


def test_political_content_is_an_error(tmp_path: Path):
    issues = inspect_post(_post(title="대통령 선거 관련 러닝 행사 안내"), tmp_path)
    assert any(issue.level == "error" and "정치 관련" in issue.message for issue in issues)


def test_thin_content_and_missing_tags_are_warnings(tmp_path: Path):
    issues = inspect_post(_post(content_html="<p>짧은 본문</p>", tags=[]), tmp_path)
    messages = [issue.message for issue in issues]
    assert any("350자 미만" in message for message in messages)
    assert any("태그" in message for message in messages)


def test_official_source_is_required(tmp_path: Path):
    issues = inspect_post(_post(sources=[]), tmp_path)
    assert any(issue.level == "error" and "공식 출처" in issue.message for issue in issues)
