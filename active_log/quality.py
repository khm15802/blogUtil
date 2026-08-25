from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
SRC_RE = re.compile(r"\bsrc\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
ALT_RE = re.compile(r"\balt\s*=\s*['\"]([^'\"]*)['\"]", re.IGNORECASE)


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

    if len(title) < 10:
        issues.append(QualityIssue("warning", "제목이 10자보다 짧습니다."))
    if len(title) > 100:
        issues.append(QualityIssue("error", "제목은 100자를 넘을 수 없습니다."))
    if len(summary) < 20:
        issues.append(QualityIssue("warning", "요약이 20자보다 짧습니다."))
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", topic_key):
        issues.append(QualityIssue("error", "식별 키는 영문 소문자, 숫자, 하이픈만 사용할 수 있습니다."))

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
