from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .content_policy import find_political_terms


IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
SRC_RE = re.compile(r"\bsrc\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
ALT_RE = re.compile(r"\balt\s*=\s*['\"]([^'\"]*)['\"]", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class QualityIssue:
    level: str
    message: str


def inspect_post(post: dict, project_root: Path | None = None) -> list[QualityIssue]:
    """Run fast, deterministic checks before a draft is published."""
    root = (project_root or Path.cwd()).resolve()
    issues: list[QualityIssue] = []

    title = str(post.get("title", "")).strip()
    summary = str(post.get("summary", "")).strip()
    content = str(post.get("content_html", "")).strip()
    topic_key = str(post.get("topic_key", "")).strip()
    sources = post.get("sources", [])
    tags = post.get("tags", [])

    political_terms = find_political_terms(post)
    if political_terms:
        issues.append(QualityIssue(
            "error", f"정치 관련 내용은 게시할 수 없습니다: {', '.join(political_terms)}"
        ))

    if len(title) < 10:
        issues.append(QualityIssue("warning", "제목이 10자보다 짧습니다."))
    if len(title) > 100:
        issues.append(QualityIssue("error", "제목은 100자를 넘을 수 없습니다."))
    if len(summary) < 20:
        issues.append(QualityIssue("warning", "요약이 20자보다 짧습니다."))
    plain_content = " ".join(TAG_RE.sub(" ", content).split())
    if len(plain_content) < 350:
        issues.append(QualityIssue("warning", "검색 독자에게 제공할 본문 정보가 부족합니다(350자 미만)."))
    if len(re.findall(r"<h2\b", content, re.IGNORECASE)) < 3:
        issues.append(QualityIssue("warning", "본문 소제목이 3개보다 적어 핵심 정보를 찾기 어렵습니다."))
    if not isinstance(tags, list) or len(tags) < 3:
        issues.append(QualityIssue("warning", "구체적인 행사명·연도·장소 태그를 3개 이상 입력하세요."))
    elif len(tags) > 10:
        issues.append(QualityIssue("warning", "태그는 핵심 검색어 위주로 10개 이하를 권장합니다."))
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", topic_key):
        issues.append(QualityIssue("error", "식별 키는 영문 소문자, 숫자, 하이픈만 사용할 수 있습니다."))

    if not sources:
        issues.append(QualityIssue("error", "공식 출처 URL이 최소 1개 필요합니다."))
    for source in sources:
        value = source.get("url", "") if isinstance(source, dict) else str(source)
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            issues.append(QualityIssue("error", f"올바르지 않은 출처 URL: {value}"))

    for index, tag in enumerate(IMG_RE.findall(content), start=1):
        alt = ALT_RE.search(tag)
        if not alt or not alt.group(1).strip():
            issues.append(QualityIssue("warning", f"{index}번째 이미지에 대체 텍스트(alt)가 없습니다."))
        src = SRC_RE.search(tag)
        if not src:
            issues.append(QualityIssue("error", f"{index}번째 이미지에 src가 없습니다."))
            continue
        value = src.group(1).strip()
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"}:
            issues.append(QualityIssue("warning", f"{index}번째 이미지는 외부 주소라 게시 후 표시되지 않을 수 있습니다."))
        elif value.startswith("data:") or value.startswith("[##_Image|"):
            continue
        else:
            candidate = (root / value.lstrip("/")).resolve()
            if not candidate.is_file():
                issues.append(QualityIssue("error", f"{index}번째 이미지 파일을 찾을 수 없습니다: {value}"))

    if not content:
        issues.append(QualityIssue("error", "본문이 비어 있습니다."))
    return issues
