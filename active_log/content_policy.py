from __future__ import annotations

import re


# 명백한 정치 주제만 차단한다. 지자체가 주최하는 일반 체육·문화 행사까지
# 과도하게 막지 않도록 "정부", "시청" 같은 일반 행정 표현은 포함하지 않는다.
POLITICAL_TERMS = (
    "정치",
    "정당",
    "대통령",
    "국회의원",
    "국회",
    "총선",
    "대선",
    "지방선거",
    "여당",
    "야당",
    "탄핵",
    "정치 집회",
    "정치 시위",
    "김대중",
)


def find_political_terms(post: dict) -> list[str]:
    """Return political terms found in reader-visible post fields."""
    tags = post.get("tags", [])
    visible_text = " ".join(
        (
            str(post.get("title", "")),
            str(post.get("summary", "")),
            str(post.get("content_html", "")),
            " ".join(str(tag) for tag in tags),
        )
    )
    plain_text = re.sub(r"<[^>]+>", " ", visible_text).casefold()
    return [term for term in POLITICAL_TERMS if term.casefold() in plain_text]


def ensure_non_political(post: dict) -> None:
    found = find_political_terms(post)
    if found:
        raise RuntimeError(f"정치 관련 내용이 감지되어 글 생성을 중단했습니다: {', '.join(found)}")
