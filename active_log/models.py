from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


ImagePosition = Literal["hero", "september", "october", "november", "closing"]


class ImageAsset(BaseModel):
    slot: str
    filename: str
    alt: str
    position: ImagePosition
    local_path: str | None = None
    image_url: HttpUrl | None = None
    tistory_tag: str | None = None
    origin_width: int | None = Field(default=None, ge=1)
    origin_height: int | None = Field(default=None, ge=1)

    @field_validator("tistory_tag")
    @classmethod
    def validate_tistory_tag(cls, value: str | None) -> str | None:
        if value and not (value.startswith("[##_Image|") and value.endswith("_##]")):
            raise ValueError("티스토리에서 복사한 이미지 태그 형식이 아닙니다.")
        return value


class EventInfo(BaseModel):
    name: str
    date: str
    location: str
    distances: str
    registration: str = "공식 홈페이지 확인"
    description: str
    official_url: HttpUrl | None = None


class SectionData(BaseModel):
    id: str
    title: str
    lead: str = ""
    paragraphs: list[str] = Field(default_factory=list)
    events: list[EventInfo] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    image_slot: str | None = None
    variant: Literal["default", "tips", "checklist"] = "default"


class SeoData(BaseModel):
    description: str = Field(min_length=20, max_length=180)
    keywords: list[str] = Field(min_length=1, max_length=12)


class PostData(BaseModel):
    schema_version: str = "1.0"
    title: str = Field(min_length=5, max_length=100)
    category: str
    subcategory: str
    date: str
    blog_name: str = "ACTIVELOG"
    views_text: str = "조회수 -"
    intro: str
    notice: str
    sections: list[SectionData]
    images: list[ImageAsset] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    seo: SeoData

    def image_by_slot(self, slot: str) -> ImageAsset | None:
        return next((image for image in self.images if image.slot == slot), None)
