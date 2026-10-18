"""Operator-assisted official OAuth code exchange; secrets never enter command arguments."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

from dotenv import set_key

from .config import Settings
from .instagram import InstagramClient, InstagramError


def request_token(url: str, params: dict, *, method: str) -> dict:
    encoded = urlencode(params).encode()
    request = Request(url + ('?' + encoded.decode() if method == 'GET' else ''),
                      data=encoded if method == 'POST' else None, method=method)
    try:
        with urlopen(request, timeout=45) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise InstagramError(
            f"토큰 교환 실패(HTTP {exc.code}). 앱 ID·Instagram 앱 시크릿·리디렉션 주소를 확인하세요. "
            "인증 코드는 한 번만 사용할 수 있으며 유효 시간이 지나면 새 승인이 필요합니다."
        ) from None
    except (URLError, OSError, ValueError):
        raise InstagramError("토큰 교환 응답을 확인하지 못했습니다. 네트워크 상태를 확인하세요.") from None
    if not isinstance(result, dict) or 'error' in result:
        raise InstagramError("토큰 교환 결과를 확인할 수 없습니다.")
    return result


def parse_callback(callback_url: str) -> tuple[str, str, str]:
    parts = urlsplit(callback_url.strip())
    if (parts.scheme, parts.netloc, parts.path) != (
        'https', 'developers.facebook.com', '/instagram/token_generator/oauth/'
    ):
        raise InstagramError("메타 토큰 생성 후 나타난 developers.facebook.com/instagram/token_generator/oauth/ 주소 전체를 입력하세요.")
    params = parse_qs(parts.query)
    if params.get('error'):
        raise InstagramError("승인되지 않은 인증 요청입니다.")
    try:
        code = params['code'][0]
        state = json.loads(params['state'][0])
        app_id, user_id = str(state['app_id']), str(state['user_id'])
        if not app_id.isdigit() or not user_id.isdigit() or not code:
            raise ValueError
    except (KeyError, ValueError, TypeError, IndexError):
        raise InstagramError("주소에 유효한 인증 코드와 앱·계정 정보가 없습니다.") from None
    return code, app_id, user_id


def connect_from_callback(callback_url: str, app_secret: str, env_path: Path = Path('.env'),
                          *, redirect_uri: str = 'https://developers.facebook.com/instagram/token_generator/oauth/',
                          expected_username: str = 'active_log.daily') -> str:
    code, app_id, user_id = parse_callback(callback_url)
    if not app_secret.strip():
        raise InstagramError("Instagram 앱 시크릿이 필요합니다.")
    short_response = request_token('https://api.instagram.com/oauth/access_token', {
        'client_id': app_id, 'client_secret': app_secret.strip(),
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri,
        'code': code,
    }, method='POST')
    try:
        short = short_response['data'][0] if 'data' in short_response else short_response
        token = short['access_token']
        # OAuth IDs can be app-scoped and differ from the tester-list ID.
        # Verify the actual username with /me before saving any token.
        permissions = short.get('permissions', [])
        if isinstance(permissions, str):
            permissions = permissions.replace(',', ' ').split()
        if not {'instagram_business_basic', 'instagram_business_content_publish'} <= set(permissions):
            raise InstagramError("프로필 조회·콘텐츠 게시 권한이 모두 필요합니다. 저장하지 않았습니다.")
    except (KeyError, IndexError, TypeError):
        raise InstagramError("정상적인 단기 토큰을 받지 못했습니다.") from None
    long = request_token('https://graph.instagram.com/access_token', {
        'grant_type': 'ig_exchange_token', 'client_secret': app_secret.strip(), 'access_token': token,
    }, method='GET')
    try:
        token = long['access_token']
        expires = int(long['expires_in'])
        if not isinstance(token, str) or not token or expires <= 0:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise InstagramError("정상적인 장기 토큰을 받지 못했습니다.") from None
    config = Settings(_env_file=None, instagram_access_token=token)
    account = InstagramClient(config).account()
    if account['username'].casefold() != expected_username.lstrip('@').casefold():
        raise InstagramError("토큰의 계정이 연결 대상 사용자 이름과 다릅니다. 저장하지 않았습니다.")
    user_id = str(account['id'])
    # Validate everything before changing any local settings. No app secret/code is stored.
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.touch(mode=0o600)
    env_path.chmod(0o600)
    set_key(str(env_path), 'INSTAGRAM_ACCESS_TOKEN', token)
    set_key(str(env_path), 'INSTAGRAM_USER_ID', user_id)
    expiry = datetime.now(timezone.utc) + timedelta(seconds=expires)
    set_key(str(env_path), 'INSTAGRAM_TOKEN_EXPIRES_AT', expiry.isoformat())
    return f"@{account['username']} 연결 완료. 토큰을 로컬 .env에 저장했습니다. 앱을 다시 시작하세요."


def connection_server(env_path: Path = Path('.env'), *, tls: bool = False):
    """One-use loopback form; no credential values in URLs, logs or responses."""
    import html
    import secrets
    from http.server import BaseHTTPRequestHandler, HTTPServer

    nonce = secrets.token_urlsafe(32)
    route = '/' + nonce

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status, body):
            payload = ("<!doctype html><html lang='ko'><meta charset='utf-8'>"
                       "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                       "<title>액티브로그 인스타 연결</title>"
                       "<style>body{font:18px sans-serif;max-width:600px;margin:60px auto;padding:20px}"
                       "input,textarea,button{display:block;box-sizing:border-box;width:100%;padding:12px;margin:12px 0}"
                       "button{background:#347b56;color:white;border:0;border-radius:8px}</style>" + body).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'same-origin')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self' https://www.instagram.com; frame-ancestors 'none'")
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def valid_host(self):
            return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

        def do_GET(self):
            if urlsplit(self.path).path == '/instagram/callback' and self.valid_host():
                params = parse_qs(urlsplit(self.path).query)
                if not secrets.compare_digest(params.get('state', [''])[0], nonce) or not self.server.app_secret:
                    return self.respond(403, '<p>인증 요청을 확인할 수 없습니다.</p>')
                callback = 'https://developers.facebook.com/instagram/token_generator/oauth/?' + urlencode({
                    'code': params.get('code', [''])[0],
                    'state': json.dumps({'app_id': self.server.app_id, 'user_id': self.server.user_id}),
                })
                try:
                    result = connect_from_callback(callback, self.server.app_secret, env_path,
                                                   redirect_uri=self.server.redirect_uri)
                except InstagramError as exc:
                    self.server.app_secret = ''
                    return self.respond(400, '<h1>연결 실패</h1><p>' + html.escape(str(exc)) + '</p>')
                self.server.app_secret = ''
                self.server.connected = True
                return self.respond(200, '<h1>연결 완료</h1><p>' + html.escape(result) + '</p>')
            if self.path != route or not self.valid_host():
                return self.respond(404, '<p>연결 화면을 찾을 수 없습니다.</p>')
            self.respond(200, "<h1>인스타그램 연결</h1><p>인증 정보를 이 컴퓨터에서만 처리합니다.</p>"
                         "<form method='post' autocomplete='off'>"
                         "<label for='callback'>메타 반환 주소</label><textarea id='callback' name='callback' required></textarea>"
                         "<label for='secret'>Instagram 앱 시크릿</label><input id='secret' name='secret' type='password' required>"
                         "<button name='mode' value='oauth'>로그인으로 연결</button>"
                         "<button name='mode' value='exchange'>기존 코드로 연결</button></form>")

        def do_POST(self):
            allowed_origins = {f'{self.server.scheme}://127.0.0.1:{self.server.server_port}', f'{self.server.scheme}://localhost:{self.server.server_port}'}
            if self.path != route or not self.valid_host() or self.headers.get('Origin') not in allowed_origins:
                return self.respond(403, '<p>허용되지 않은 요청입니다.</p>')
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384:
                    raise ValueError
                values = parse_qs(self.rfile.read(length).decode())
                if values.get('mode') == ['oauth']:
                    _, app_id, user_id = parse_callback(values.get('callback', [''])[0])
                    secret = values.get('secret', [''])[0].strip()
                    if not secret:
                        raise InstagramError('Instagram 앱 시크릿이 필요합니다.')
                    self.server.app_id, self.server.user_id, self.server.app_secret = app_id, user_id, secret
                    location = 'https://www.instagram.com/oauth/authorize?' + urlencode({
                        'client_id': app_id, 'redirect_uri': self.server.redirect_uri,
                        'response_type': 'code', 'scope': 'instagram_business_basic,instagram_business_content_publish',
                        'state': nonce,
                    })
                    self.send_response(303)
                    self.send_header('Location', location)
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                result = connect_from_callback(values.get('callback', [''])[0], values.get('secret', [''])[0], env_path)
            except InstagramError as exc:
                return self.respond(400, '<h1>연결을 완료하지 못했습니다</h1><p>' + html.escape(str(exc)) + '</p>')
            except (ValueError, OSError):
                return self.respond(400, '<p>입력 또는 저장 중 오류가 발생했습니다. 비밀값은 표시하지 않습니다.</p>')
            self.server.connected = True
            self.respond(200, '<h1>연결 완료</h1><p>' + html.escape(result) + '</p>')

    server = HTTPServer(('127.0.0.1', 8766), Handler)
    server.connected = False
    server.app_secret = ''
    server.scheme = 'https' if tls else 'http'
    server.redirect_uri = f'{server.scheme}://localhost:{server.server_port}/instagram/callback'
    server.timeout = 1
    if tls:
        import ssl
        import subprocess
        import shutil
        directory = Path('output/instagram-local-tls')
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        config_file = directory / 'openssl.cnf'
        config_file.write_text("[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n"
                               "[dn]\nCN=localhost\n[ext]\nsubjectAltName=DNS:localhost,IP:127.0.0.1\n")
        key, cert = directory / 'key.pem', directory / 'cert.pem'
        openssl = shutil.which('openssl')
        if not openssl and os.name == 'nt':
            for root in (os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)')):
                if root:
                    candidate = Path(root) / 'Git' / 'usr' / 'bin' / 'openssl.exe'
                    if candidate.is_file():
                        openssl = str(candidate)
                        break
        try:
            if not openssl:
                raise OSError('openssl not found')
            valid = key.is_file() and cert.is_file() and subprocess.run(
                [openssl, 'x509', '-in', str(cert), '-noout', '-checkend', '600'],
                capture_output=True,
            ).returncode == 0
            if not valid:
                subprocess.run([openssl, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                                '-keyout', str(key), '-out', str(cert), '-config', str(config_file)],
                               check=True, capture_output=True)
            key.chmod(0o600)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            server.socket = context.wrap_socket(server.socket, server_side=True)
        except (OSError, subprocess.CalledProcessError):
            server.server_close()
            raise InstagramError('로컬 HTTPS 인증서를 만들지 못했습니다. OpenSSL 설치를 확인하세요.') from None
    return server, f'{server.scheme}://localhost:{server.server_port}{route}'


def serve_connection() -> None:
    import time
    server, url = connection_server(tls=True)
    print(f'브라우저 연결 화면: {url}', flush=True)
    print('10분간 대기합니다. 연결 완료 후 자동 종료됩니다.', flush=True)
    deadline = time.monotonic() + 600
    try:
        while not server.connected and time.monotonic() < deadline:
            server.handle_request()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    print('연결 완료' if server.connected else '연결 대기 시간 종료', flush=True)
