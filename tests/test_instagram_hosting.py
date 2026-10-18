import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock

import pytest

from active_log.config import Settings
from active_log.instagram import InstagramError
from active_log.instagram_hosting import _download_cloudflared, _image_file, instagram_media_base


def test_temporary_image_server_path_is_limited_to_generated_jpegs(tmp_path):
    root = tmp_path.resolve()
    folder = root / ("a" * 32)
    folder.mkdir()
    image = folder / "01.jpg"
    image.write_bytes(b"jpeg")

    assert _image_file(root, f"/{'a' * 32}/01.jpg") == image
    assert _image_file(root, f"/{'a' * 32}/11.jpg") is None
    assert _image_file(root, f"/{'a' * 32}/caption.txt") is None
    assert _image_file(root, "/") is None
    assert _image_file(root, f"/{'a' * 32}/../secret.jpg") is None


@pytest.mark.parametrize("valid_digest", [True, False])
def test_cloudflared_download_requires_github_sha256(tmp_path, monkeypatch, valid_digest):
    binary = b"official tunnel binary"
    digest = hashlib.sha256(binary).hexdigest()
    metadata = {
        "tag_name": "2026.10.1",
        "assets": [{
            "name": "cloudflared-windows-amd64.exe",
            "browser_download_url": "https://release.example/cloudflared.exe",
            "digest": f"sha256:{digest if valid_digest else '0' * 64}",
        }],
    }

    class Response:
        def __init__(self, content):
            self.content = content

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self.content

    def fake_urlopen(request, **_kwargs):
        if "api.github.com" in request.full_url:
            return Response(json.dumps(metadata).encode())
        return Response(binary)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("active_log.instagram_hosting.sys.platform", "win32")
    monkeypatch.setattr("active_log.instagram_hosting.platform.machine", lambda: "AMD64")
    monkeypatch.setattr("active_log.instagram_hosting.shutil.which", lambda _name: None)
    monkeypatch.setattr("active_log.instagram_hosting.urlopen", fake_urlopen)

    if valid_digest:
        path = _download_cloudflared()
        assert path.read_bytes() == binary
        assert path.name == "cloudflared.exe"
    else:
        with pytest.raises(InstagramError, match="체크섬"):
            _download_cloudflared()
        assert not (tmp_path / "data/tools/cloudflared/2026.10.1/cloudflared.exe").exists()


def test_configured_public_host_skips_quick_tunnel(monkeypatch, tmp_path):
    config = Settings(_env_file=None, instagram_media_dir=tmp_path,
                      instagram_media_base_url="https://media.example/cards")
    monkeypatch.setattr("active_log.instagram_hosting.InstagramImageTunnel",
                        lambda *_args: pytest.fail("configured host should bypass tunnel"))

    with instagram_media_base(config) as base_url:
        assert base_url == "https://media.example/cards"


def test_service_uses_temporary_host_for_carousel_then_publishes(monkeypatch, tmp_path):
    # This is an integration seam test: the automatic host URL must reach card
    # generation and the API publisher without changing the saved settings.
    import asyncio
    from active_log.db import Database
    from active_log.service import AutomationService

    db = Database(tmp_path / "test.db")
    post_id = db.save_post({
        "topic_key": "test-event", "category": "러닝", "title": "테스트 행사",
        "summary": "테스트 안내", "content_html": "<p>테스트</p>", "tags": [], "sources": [],
    })
    config = Settings(_env_file=None, instagram_media_dir=tmp_path / "media")
    service = AutomationService(config, db)

    @contextmanager
    def fake_host(_config):
        yield "https://temporary.example"

    prepared = Mock(return_value=([
        "https://temporary.example/folder/01.jpg", "https://temporary.example/folder/02.jpg",
    ], "caption"))
    publisher = Mock()
    publisher.publish.return_value = "https://www.instagram.com/p/example/"
    monkeypatch.setattr("active_log.instagram_hosting.instagram_media_base", fake_host)
    monkeypatch.setattr(service, "prepare_instagram", prepared)
    monkeypatch.setattr("active_log.instagram.InstagramPublisher", lambda *_args: publisher)
    result = asyncio.run(service.publish_instagram(post_id))

    assert result == "https://www.instagram.com/p/example/"
    prepared.assert_called_once()
    assert prepared.call_args.kwargs["config"].instagram_media_base_url == "https://temporary.example"
    assert config.instagram_media_base_url == ""
