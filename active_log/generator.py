import hashlib
import json
from datetime import date

from openai import OpenAI


CATEGORIES = ["러닝", "자전거", "캠핑·레저", "행사·이벤트"]

POST_SCHEMA = {
    "type": "object",
    "properties": {
        "topic_key": {"type": "string"},
        "category": {"type": "string", "enum": CATEGORIES},
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "content_html": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 10},
    },
    "required": ["topic_key", "category", "title", "summary", "content_html", "tags"],
    "additionalProperties": False,
}


class PostGenerator:
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, category: str, recent_keys: list[str]) -> dict:
        today = date.today().isoformat()
        response = self.client.responses.create(
            model=self.model,
            tools=[{"type": "web_search"}],
            instructions=(
                "당신은 한국의 러닝·자전거·캠핑·레저 일정 전문 에디터다. "
                "공식 주최기관이나 공식 행사 페이지를 우선 검색한다. 확인되지 않은 날짜, 장소, 가격은 쓰지 않는다. "
                "다른 글을 복제하지 말고 사실을 토대로 새 글을 작성한다. 본문은 티스토리에 붙일 수 있는 깔끔한 HTML로 작성한다. "
                "본문 마지막에 '정보 확인일'과 '참고 및 공식 안내' 섹션을 두고 출처 링크를 포함한다. "
                "종료된 행사를 현재 신청 가능한 것처럼 소개하지 않는다. 광고성 과장 표현을 피한다. "
                "정치, 정당, 선거, 정치인, 정치 집회·시위, 정치적 논쟁이나 이념과 관련된 주제는 선정하지 않는다. "
                "정치인의 이름을 내건 행사도 제외한다. 정치와 무관한 생활 체육·여가·문화 행사만 작성한다. "
                "ACTIVELOG의 문체는 현장에서 바로 확인할 수 있는 실용 정보를 차분하게 건네는 생활형 매거진 문체다. "
                "'알아보겠습니다', '완벽 가이드', '총정리해 보았습니다', '도움이 되셨길 바랍니다' 같은 상투어를 쓰지 않는다. "
                "모든 문단을 같은 길이로 만들지 말고 짧은 문장과 긴 문장을 자연스럽게 섞는다. "
                "번호 목록을 습관적으로 반복하지 말고 주제에 맞는 구조를 선택한다. 당연한 말과 내용 없는 결론은 삭제한다. "
                "작성자가 직접 경험하지 않은 일을 체험담처럼 꾸미지 않는다. 확인된 사실, 실용적인 판단 기준, 주의할 점을 구분한다."
            ),
            input=(
                f"오늘은 {today}이다. 카테고리 '{category}'에서 한국 독자에게 유용한 최신 주제 하나를 선정해 글을 작성하라. "
                f"최근 사용한 주제 키는 {json.dumps(recent_keys[-50:], ensure_ascii=False)}이며 중복을 피하라. "
                "topic_key는 행사명-연도 또는 핵심주제-연월처럼 재사용 가능한 짧은 식별자로 작성하라."
            ),
            text={
                "format": {
                    "type": "json_schema", "name": "active_log_post", "strict": True, "schema": POST_SCHEMA
                }
            },
        )
        post = json.loads(response.output_text)
        post["sources"] = self._extract_sources(response)
        if not post["sources"]:
            raise RuntimeError("출처를 확인할 수 없어 글 생성을 중단했습니다.")
        post["topic_key"] = self._normalize_key(post["topic_key"])
        if post["topic_key"] in recent_keys:
            raise RuntimeError("최근 글과 중복된 주제가 생성되었습니다.")
        return post

    @staticmethod
    def _extract_sources(response) -> list[dict]:
        found: dict[str, str] = {}
        for item in response.output:
            for content in getattr(item, "content", []) or []:
                for annotation in getattr(content, "annotations", []) or []:
                    url = getattr(annotation, "url", None)
                    if url:
                        found[url] = getattr(annotation, "title", None) or url
        return [{"title": title, "url": url} for url, title in found.items()]

    @staticmethod
    def _normalize_key(value: str) -> str:
        normalized = "-".join(value.strip().lower().split())[:180]
        return normalized or hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
