import html
import json
import re

from .models import ImageAsset, PostData


TAG_PATTERN = re.compile(r"\[##_Image\|.*?_\#\#\]")
META_PATTERN = re.compile(r"\|(\{.*\})_\#\#\]$")


def parse_tistory_tags(text: str) -> dict[str, str]:
    """티스토리에서 복사한 태그를 filename 기준으로 반환한다."""
    result: dict[str, str] = {}
    for raw_tag in TAG_PATTERN.findall(html.unescape(text)):
        match = META_PATTERN.search(raw_tag)
        if not match:
            continue
        try:
            filename = json.loads(match.group(1)).get("filename")
        except json.JSONDecodeError:
            continue
        if filename:
            result[filename] = raw_tag
    return result


def attach_tistory_tags(post: PostData, text: str) -> tuple[PostData, list[str]]:
    tags = parse_tistory_tags(text)
    images: list[ImageAsset] = []
    missing: list[str] = []
    for image in post.images:
        tag = tags.get(image.filename)
        if not tag:
            missing.append(image.filename)
        images.append(image.model_copy(update={"tistory_tag": tag or image.tistory_tag}))
    return post.model_copy(update={"images": images}), missing
