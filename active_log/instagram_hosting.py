"""Short-lived public image delivery for Instagram carousel uploads."""
from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .config import Settings
from .instagram import InstagramError


_TUNNEL_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.I)
_VERSION = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


def _asset_name() -> tuple[str, bool]:
    system = sys.platform
    machine = platform.machine().lower()
    if system == "win32":
        if machine not in {"amd64", "x86_64", "arm64", "aarch64"}:
            raise InstagramError("Cloudflare 임시 이미지 전달은 Windows 64비트에서 사용할 수 있습니다.")
        return "cloudflared-windows-amd64.exe", False
    if system == "darwin":
        arch = "arm64" if machine in {"arm64", "aarch64"} else "amd64" if machine in {"amd64", "x86_64"} else ""
        if arch:
            return f"cloudflared-darwin-{arch}.tgz", True
    if system.startswith("linux"):
        arch = "arm64" if machine in {"arm64", "aarch64"} else "amd64" if machine in {"amd64", "x86_64"} else ""
        if arch:
            return f"cloudflared-linux-{arch}", False
    raise InstagramError("이 운영체제와 CPU에서 Cloudflare 임시 이미지 전달을 지원하지 않습니다.")


def _image_file(root: Path, request_path: str) -> Path | None:
    match = re.fullmatch(r"/([0-9a-f]{32})/(0[1-9]|10)\.jpg", urlsplit(request_path).path)
    if not match:
        return None
    candidate = (root / match.group(1) / f"{match.group(2)}.jpg").resolve()
    if root not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def _download_cloudflared(configured_path: Path | None = None) -> Path:
    configured = str(configured_path or os.environ.get("CLOUDFLARED_PATH", "")).strip()
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return path
        raise InstagramError("CLOUDFLARED_PATH 파일을 찾을 수 없습니다.")
    found = shutil.which("cloudflared")
    if found:
        return Path(found)

    name, is_archive = _asset_name()
    executable_name = "cloudflared.exe" if sys.platform == "win32" else "cloudflared"
    cache_root = Path("data/tools/cloudflared")
    cached = sorted(
        (path for path in cache_root.glob(f"*/{executable_name}") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if cached:
        return cached[0]
    metadata_request = Request(
        "https://api.github.com/repos/cloudflare/cloudflared/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Active-Log-Instagram-Publisher"},
    )
    try:
        with urlopen(metadata_request, timeout=20) as response:
            release = json.load(response)
        version = str(release.get("tag_name", ""))
        asset = next(item for item in release.get("assets", []) if item.get("name") == name)
        digest = str(asset.get("digest", ""))
        if not _VERSION.fullmatch(version) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise ValueError
        with urlopen(Request(asset["browser_download_url"], headers={"User-Agent": "Active-Log"}), timeout=60) as response:
            artifact = response.read()
    except (URLError, TimeoutError, OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError):
        raise InstagramError("Cloudflare 이미지 전달 도구를 내려받지 못했습니다. 네트워크와 GitHub 접속을 확인하세요.") from None
    if hashlib.sha256(artifact).hexdigest() != digest.removeprefix("sha256:"):
        raise InstagramError("Cloudflare 이미지 전달 도구의 체크섬이 일치하지 않습니다.")

    target = cache_root / version / executable_name
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        if is_archive:
            with tarfile.open(fileobj=io.BytesIO(artifact), mode="r:gz") as archive:
                member = archive.getmember("cloudflared")
                if not member.isfile():
                    raise ValueError
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError
                binary = source.read()
        else:
            binary = artifact
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_bytes(binary)
        if sys.platform != "win32":
            temporary.chmod(0o700)
        temporary.replace(target)
    except (OSError, KeyError, ValueError, tarfile.TarError):
        raise InstagramError("Cloudflare 이미지 전달 도구를 설치하지 못했습니다.") from None
    return target


class _ImageServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class InstagramImageTunnel:
    """Expose only generated carousel JPEGs through an ephemeral HTTPS tunnel."""

    def __init__(self, media_dir: Path, cloudflared_path: Path | None = None):
        self.media_dir = media_dir.resolve()
        self.cloudflared_path = cloudflared_path
        self.http: _ImageServer | None = None
        self.http_thread: threading.Thread | None = None
        self.process: subprocess.Popen[str] | None = None
        self.base_url = ""

    def __enter__(self) -> str:
        self.media_dir.mkdir(parents=True, exist_ok=True)
        root = self.media_dir

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self._serve(send_body=True)

            def do_HEAD(self):  # noqa: N802
                self._serve(send_body=False)

            def _serve(self, *, send_body: bool):
                candidate = _image_file(root, self.path)
                if candidate is None:
                    self.send_error(404)
                    return
                try:
                    size = candidate.stat().st_size
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(size))
                    self.send_header("Cache-Control", "public, max-age=300")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    if send_body:
                        with candidate.open("rb") as stream:
                            shutil.copyfileobj(stream, self.wfile)
                except OSError:
                    self.send_error(404)

            def log_message(self, _format, *_args):
                return

        self.http = _ImageServer(("127.0.0.1", 0), Handler)
        self.http_thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.http_thread.start()
        try:
            executable = _download_cloudflared(self.cloudflared_path)
            local_url = f"http://127.0.0.1:{self.http.server_port}"
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
            self.process = subprocess.Popen(
                [str(executable), "tunnel", "--no-autoupdate", "--url", local_url],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
            lines: queue.Queue[str | None] = queue.Queue()

            def read_output() -> None:
                assert self.process and self.process.stdout
                for line in self.process.stdout:
                    lines.put(line)
                lines.put(None)

            threading.Thread(target=read_output, daemon=True).start()
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise InstagramError("Cloudflare 임시 이미지 연결을 시작하지 못했습니다. 네트워크를 확인하세요.")
                try:
                    line = lines.get(timeout=0.5)
                except queue.Empty:
                    continue
                if line is None:
                    break
                match = _TUNNEL_URL.search(line)
                if match:
                    self.base_url = match.group(0)
                    return self.base_url
            raise InstagramError("Cloudflare 임시 이미지 연결 대기 시간이 초과됐습니다.")
        except InstagramError:
            self.close()
            raise
        except Exception:
            self.close()
            raise InstagramError("임시 HTTPS 이미지 전달을 시작하지 못했습니다.") from None

    def close(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None
        if self.http:
            self.http.shutdown()
            self.http.server_close()
            self.http = None

    def __exit__(self, _type, _value, _traceback) -> None:
        self.close()


@contextmanager
def instagram_media_base(config: Settings) -> Iterator[str]:
    configured = config.instagram_media_base_url.strip()
    if configured:
        yield configured
        return
    with InstagramImageTunnel(config.instagram_media_dir, config.cloudflared_path) as base_url:
        yield base_url
