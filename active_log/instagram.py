"""Official Instagram Login API publishing; no browser login or passwords."""
from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from .config import Settings
from .content_policy import ensure_non_political
from .db import Database


class InstagramError(RuntimeError):
    pass


class InstagramClient:
    def __init__(self, config: Settings):
        self.config = config
        if not config.instagram_access_token.get_secret_value():
            raise InstagramError("INSTAGRAM_ACCESS_TOKEN을 로컬 .env에 설정하세요.")
        self.base = f"https://graph.instagram.com/{config.instagram_api_version}"

    def request(self, method: str, path: str, **params) -> dict:
        token = self.config.instagram_access_token.get_secret_value()
        encoded = urlencode(params).encode()
        url = f"{self.base}/{path}"
        if method == "GET" and params:
            url += "?" + encoded.decode()
        request = Request(url, data=encoded if method == "POST" else None, method=method,
                          headers={"Authorization": f"Bearer {token}"})
        try:
            with urlopen(request, timeout=45) as response:
                result = json.load(response)
        except HTTPError as exc:
            # Never expose the provider's raw response, URLs, or token in logs.
            try:
                code = json.loads(exc.read()).get("error", {}).get("code", "unknown")
            except (ValueError, AttributeError):
                code = "unknown"
            raise InstagramError(f"인스타그램 API 요청 실패(HTTP {exc.code}, 코드 {code}). 권한·토큰·계정 상태를 확인하세요.") from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise InstagramError("인스타그램 API 응답을 확인하지 못했습니다. 연결 상태를 확인하세요.") from None
        if not isinstance(result, dict) or "error" in result:
            raise InstagramError("인스타그램 API가 정상 결과를 반환하지 않았습니다.")
        return result

    def account(self) -> dict:
        account = self.request("GET", "me", fields="user_id,username")
        account_id = str(account.get("user_id") or account.get("id") or "")
        if not account_id.isdigit() or not account.get("username"):
            raise InstagramError("프로페셔널 계정 정보를 확인할 수 없습니다.")
        if self.config.instagram_user_id and account_id != self.config.instagram_user_id:
            raise InstagramError("토큰의 계정과 INSTAGRAM_USER_ID가 다릅니다. 연결할 계정을 확인하세요.")
        return {"id": account_id, "username": account["username"]}

    def wait_ready(self, container_id: str) -> None:
        for _ in range(30):
            state = self.request("GET", container_id, fields="status_code").get("status_code")
            if state == "FINISHED":
                return
            if state in {"ERROR", "EXPIRED", "PUBLISHED"}:
                raise InstagramError(f"인스타그램 이미지 처리 상태: {state}")
            time.sleep(2)
        raise InstagramError("인스타그램 이미지 처리 대기 시간이 초과됐습니다.")

    def create_carousel(self, account_id: str, urls: list[str], caption: str) -> str:
        children = []
        for url in urls:
            child = str(self.request("POST", f"{account_id}/media", image_url=url,
                                     is_carousel_item="true")["id"])
            self.wait_ready(child)
            children.append(child)
        parent = str(self.request("POST", f"{account_id}/media", media_type="CAROUSEL",
                                  children=",".join(children), caption=caption)["id"])
        self.wait_ready(parent)
        return parent


def prepare_cards(config: Settings, post: dict, poster: Path | None) -> tuple[list[str], str]:
    """Write JPEGs to an operator-configured, publicly served directory."""
    base = urlsplit(config.instagram_media_base_url)
    if base.scheme != "https" or not base.hostname or base.username or base.query or base.fragment:
        raise InstagramError("INSTAGRAM_MEDIA_BASE_URL에 카드 폴더를 제공하는 공개 HTTPS 주소를 설정하세요.")
    ensure_non_political(post)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QImage
    from .instagram_cards import generate_instagram_cards

    folder = secrets.token_hex(16)
    output = config.instagram_media_dir / folder
    paths = generate_instagram_cards(post, output, poster)
    caption = (output / "caption.txt").read_text(encoding="utf-8").strip()
    if not 2 <= len(paths) <= 10 or len(caption) > 2200:
        raise InstagramError("카드는 2~10장, 설명문은 2,200자 이하여야 합니다.")
    urls = []
    for index, path in enumerate(paths, 1):
        image = QImage(str(path)).convertToFormat(QImage.Format_RGB32)
        target = output / f"{index:02d}.jpg"
        if image.isNull() or not image.save(str(target), "JPEG", 92) or target.stat().st_size > 8 * 1024 * 1024:
            raise InstagramError("게시용 JPEG 카드 변환에 실패했습니다.")
        urls.append(f"{config.instagram_media_base_url.rstrip('/')}/{folder}/{target.name}")
    return urls, caption


class InstagramPublisher:
    def __init__(self, config: Settings, db: Database, client=None):
        self.config, self.db = config, db
        self.client = client or InstagramClient(config)

    def publish(self, post_id: int, urls: list[str], caption: str) -> str:
        if not 2 <= len(urls) <= 10 or not caption.strip() or len(caption) > 2200:
            raise InstagramError("카드 2~10장과 2,200자 이하 설명문이 필요합니다.")
        if any(urlsplit(url).scheme != "https" for url in urls):
            raise InstagramError("카드 이미지 주소는 HTTPS여야 합니다.")
        post = self.db.get_post(post_id)
        if not post:
            raise KeyError(f"글 {post_id}을 찾을 수 없습니다.")
        ensure_non_political(post)
        account = self.client.account()
        account_id = account["id"]
        self.db.claim_instagram(post_id, account_id)
        publishing = False
        try:
            parent = self.client.create_carousel(account_id, urls, caption)
            # Persist before sending: a timeout/crash after this point must not cause a duplicate.
            self.db.update_instagram(post_id, account_id, "publishing", container_id=parent)
            publishing = True
            result = self.client.request("POST", f"{account_id}/media_publish", creation_id=parent)
            media_id = str(result["id"])
            self.db.update_instagram(post_id, account_id, "published", media_id=media_id)
        except Exception:
            self.db.update_instagram(post_id, account_id, "unknown" if publishing else "failed")
            raise InstagramError(
                "게시 결과를 확인할 수 없습니다. 인스타그램에서 확인 후 상태를 복구하세요. 자동 재게시는 차단됐습니다."
                if publishing else "인스타그램 게시 준비에 실패했습니다. 계정 권한과 공개 이미지 주소를 확인하세요."
            ) from None
        # A permalink lookup failure cannot turn a successful post into a failed one.
        try:
            url = self.client.request("GET", media_id, fields="permalink").get("permalink", "")
        except InstagramError:
            url = ""
        return url or f"게시 완료 (미디어 ID: {media_id})"

    def reconcile(self, post_id: int) -> str:
        account_id = self.client.account()["id"]
        row = next((row for row in self.db.list_instagram_publications()
                    if row["post_id"] == post_id and row["account_id"] == account_id), None)
        if not row or not row["container_id"]:
            raise InstagramError("조회할 컨테이너가 없습니다. 실제 피드와 게시 이력을 확인하세요.")
        if row["status"] == "published":
            return "이미 게시 완료로 기록되어 있습니다."
        state = self.client.request("GET", row["container_id"], fields="status_code").get("status_code")
        if state == "PUBLISHED":
            self.db.update_instagram(post_id, account_id, "published")
            return "Meta에서 게시 완료를 확인했습니다. 중복 차단을 유지합니다."
        if state in {"ERROR", "EXPIRED"}:
            self.db.update_instagram(post_id, account_id, "failed")
            return f"Meta 처리 상태 {state}: 다시 게시할 수 있습니다."
        return f"Meta 처리 상태 {state}: 결과를 확정할 수 없어 재게시 차단을 유지합니다."
