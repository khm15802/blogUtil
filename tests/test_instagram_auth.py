import json
from urllib.parse import urlencode
from unittest.mock import Mock

import pytest
from dotenv import dotenv_values

from active_log.instagram import InstagramError
from active_log.instagram_auth import connect_from_callback, parse_callback


def callback():
    return 'https://developers.facebook.com/instagram/token_generator/oauth/?' + urlencode({
        'code': 'one-time-code', 'state': json.dumps({'app_id':'123', 'user_id':'456'})}) + '#_'


def test_parse_callback_uses_exact_redirect_and_ignores_fragment():
    assert parse_callback(callback()) == ('one-time-code', '123', '456')
    with pytest.raises(InstagramError):
        parse_callback(callback().replace('developers.facebook.com', 'evil.example'))


def test_connect_validates_permissions_account_and_preserves_env(tmp_path, monkeypatch):
    env = tmp_path / '.env'
    env.write_text('BLOG_NAME=keep-me\n# existing comment\n', encoding='utf-8')
    request = Mock(side_effect=[{
        'data': [{'access_token':'short', 'user_id':'456',
                  'permissions':'instagram_business_basic,instagram_business_content_publish'}]},
        {'access_token':'long-secret-token', 'expires_in': 5184000}])
    monkeypatch.setattr('active_log.instagram_auth.request_token', request)
    monkeypatch.setattr('active_log.instagram_auth.InstagramClient.account', lambda _: {'id':'456','username':'active_log.daily'})
    result = connect_from_callback(callback(), 'app-secret', env)
    values = dotenv_values(env)
    assert values['BLOG_NAME'] == 'keep-me'
    assert values['INSTAGRAM_ACCESS_TOKEN'] == 'long-secret-token'
    assert values['INSTAGRAM_USER_ID'] == '456'
    assert env.stat().st_mode & 0o777 == 0o600
    assert '# existing comment' in env.read_text()
    assert 'app-secret' not in env.read_text()
    assert 'one-time-code' not in env.read_text()
    assert 'long-secret-token' not in result


@pytest.mark.parametrize('username,permissions', [('wrong-account','instagram_business_basic,instagram_business_content_publish'),
                                               ('active_log.daily','instagram_business_basic')])
def test_invalid_account_or_permissions_leaves_env_untouched(tmp_path, monkeypatch, username, permissions):
    env = tmp_path / '.env'
    env.write_text('BLOG_NAME=keep-me\n')
    monkeypatch.setattr('active_log.instagram_auth.request_token', lambda *a, **kw: {
        'access_token':'secret', 'user_id':'999', 'permissions':permissions, 'expires_in':5184000})
    monkeypatch.setattr('active_log.instagram_auth.InstagramClient.account', lambda _: {'id':'999', 'username':username})
    with pytest.raises(InstagramError):
        connect_from_callback(callback(), 'secret', env)
    assert env.read_text() == 'BLOG_NAME=keep-me\n'


def test_loopback_oauth_form_and_callback_without_real_network(tmp_path, monkeypatch):
    import io
    from urllib.parse import parse_qs, urlsplit
    import http.server
    from active_log.instagram_auth import connection_server

    class FakeServer:
        def __init__(self, address, handler):
            self.server_port = address[1]
            self.handler = handler
    monkeypatch.setattr(http.server, 'HTTPServer', FakeServer)
    server, url = connection_server(tmp_path / '.env')
    route = urlsplit(url).path

    class Socket:
        def __init__(self, request):
            self.input = io.BytesIO(request)
            self.output = bytearray()
        def makefile(self, *args):
            return self.input
        def sendall(self, data):
            self.output.extend(data)

    def call(method, path, body='', origin=None):
        headers = f'{method} {path} HTTP/1.0\r\nHost: localhost:8766\r\n'
        if origin:
            headers += f'Origin: {origin}\r\n'
        headers += f'Content-Length: {len(body.encode())}\r\n\r\n'
        sock = Socket((headers + body).encode())
        server.handler(sock, ('127.0.0.1', 1), server)
        return sock.output.decode()

    form = call('GET', route)
    assert 'Referrer-Policy: same-origin' in form
    assert 'frame-ancestors' in form
    body = urlencode({'callback': callback(), 'secret': 'private-app-secret', 'mode': 'oauth'})
    assert '403' in call('POST', route, body, 'https://evil.example')
    response = call('POST', route, body, 'http://localhost:8766')
    assert '303' in response
    assert 'private-app-secret' not in response
    location = next(line[10:] for line in response.split('\r\n') if line.startswith('Location: '))
    params = parse_qs(urlsplit(location).query)
    assert params['scope'] == ['instagram_business_basic,instagram_business_content_publish']
    assert '403' in call('GET', '/instagram/callback?code=abc&state=wrong')
    exchange = Mock(return_value='계정 연결 완료')
    monkeypatch.setattr('active_log.instagram_auth.connect_from_callback', exchange)
    result = call('GET', '/instagram/callback?' + urlencode({'code':'new-code', 'state':params['state'][0]}))
    assert '200' in result and server.connected
    assert server.app_secret == ''
    assert exchange.call_args.kwargs == {'redirect_uri':'http://localhost:8766/instagram/callback'}


def test_app_scoped_id_can_differ_when_verified_username_matches(tmp_path, monkeypatch):
    monkeypatch.setattr('active_log.instagram_auth.request_token', Mock(side_effect=[
        {'access_token':'short', 'user_id':'999',
         'permissions':'instagram_business_basic,instagram_business_content_publish'},
        {'access_token':'long', 'expires_in':5184000},
    ]))
    monkeypatch.setattr('active_log.instagram_auth.InstagramClient.account',
                        lambda _: {'id':'777', 'username':'active_log.daily'})
    env = tmp_path / '.env'
    connect_from_callback(callback(), 'secret', env)
    assert dotenv_values(env)['INSTAGRAM_USER_ID'] == '777'
