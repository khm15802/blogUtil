from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-5-mini"
    blog_url: str = "https://active-log.tistory.com"
    blog_name: str = "active-log"
    publish_visibility: Literal["private", "public"] = "public"
    auto_publish: bool = False
    min_interval_days: int = Field(default=1, ge=1, le=30)
    max_interval_days: int = Field(default=3, ge=1, le=30)
    timezone: str = "Asia/Seoul"
    tistory_headless: bool = True
    tistory_profile_dir: Path = Path("playwright-profile")
    database_path: Path = Path("data/active_log.db")
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)

    @model_validator(mode="after")
    def validate_interval(self) -> "Settings":
        if self.min_interval_days > self.max_interval_days:
            raise ValueError("MIN_INTERVAL_DAYS는 MAX_INTERVAL_DAYS보다 클 수 없습니다.")
        return self


settings = Settings()
