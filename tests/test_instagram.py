from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import SecretStr

from active_log.config import Settings
from active_log.db import Database
from active_log.instagram import InstagramClient, InstagramError, InstagramPublisher, prepare_cards


@pytest.fixture
def db(tmp_path):
    db = Database(tmp_path / 'test.db')
    db.save_post(dict(topic_key='event', category='러닝', title='달리기 행사', summary='달리기 안내',
                      content_html='<p>행사 안내</p>', tags=[], sources=[]))
    return db


class Client:
    def __init__(self):
        self.calls = []
        self.fail_publish = False
        self.fail_prepare = False
        self.fail_link = False

    def account(self):
        return {'id': '123', 'username': 'active_log'}

    def create_carousel(self, account_id, urls, caption):
        self.calls.append('create')
        if self.fail_prepare:
            raise InstagramError('prepare error')
        return 'container'

    def request(self, method, path, **params):
        self.calls.append(path)
        if path.endswith('/media_publish'):
            if self.fail_publish:
                raise InstagramError('timeout')
            return {'id': '456'}
        if self.fail_link:
            raise InstagramError('link error')
        return {'permalink': 'https://www.instagram.com/p/example/'}


def publish(db, client):
    return InstagramPublisher(Settings(_env_file=None), db, client).publish(
        1, ['https://cdn.example/01.jpg', 'https://cdn.example/02.jpg'], '행사 안내')


def test_success_blocks_duplicate_for_same_account(db):
    client = Client()
    assert publish(db, client).startswith('https://www.instagram.com/')
    with pytest.raises(RuntimeError):
        publish(db, client)
    assert client.calls.count('123/media_publish') == 1
    assert db.list_instagram_publications()[0]['status'] == 'published'
    assert db.get_post(1)['status'] == 'draft'  # Tistory state is independent.


def test_publish_timeout_blocks_automatic_retry(db):
    client = Client()
    client.fail_publish = True
    with pytest.raises(InstagramError, match='자동 재게시'):
        publish(db, client)
    assert db.list_instagram_publications()[0]['container_id'] == 'container'
    assert db.list_instagram_publications()[0]['status'] == 'unknown'
    with pytest.raises(RuntimeError):
        publish(db, client)
    assert client.calls.count('123/media_publish') == 1


def test_preparation_failure_can_retry(db):
    client = Client()
    client.fail_prepare = True
    with pytest.raises(InstagramError):
        publish(db, client)
    assert db.list_instagram_publications()[0]['status'] == 'failed'
    client.fail_prepare = False
    publish(db, client)
    assert db.list_instagram_publications()[0]['status'] == 'published'


def test_link_failure_does_not_lose_published_state(db):
    client = Client()
    client.fail_link = True
    assert '456' in publish(db, client)
    assert db.list_instagram_publications()[0]['status'] == 'published'


def test_claim_blocks_competing_worker_and_crash(db):
    db.claim_instagram(1, '123')
    with pytest.raises(RuntimeError):
        db.claim_instagram(1, '123')
    db.claim_instagram(1, '999')  # Separate account has separate publication state.


def test_account_mismatch_and_secret_not_displayed():
    config = Settings(_env_file=None, instagram_access_token=SecretStr('private-token'), instagram_user_id='999')
    assert 'private-token' not in repr(config)
    client = InstagramClient(config)
    client.request = Mock(return_value={'user_id': '123', 'username': 'test'})
    with pytest.raises(InstagramError, match='다릅니다'):
        client.account()


def test_carousel_api_order():
    client = InstagramClient(Settings(_env_file=None, instagram_access_token='secret'))
    client.request = Mock(side_effect=[{'id':'a'}, {'status_code':'FINISHED'},
                                      {'id':'b'}, {'status_code':'FINISHED'},
                                      {'id':'parent'}, {'status_code':'FINISHED'}])
    assert client.create_carousel('123', ['https://cdn/1.jpg', 'https://cdn/2.jpg'], 'caption') == 'parent'
    assert client.request.call_args_list[4].kwargs == dict(media_type='CAROUSEL', children='a,b', caption='caption')


def test_api_errors_never_include_token(monkeypatch):
    from urllib.error import URLError
    client = InstagramClient(Settings(_env_file=None, instagram_access_token='private-token'))
    def failed(*args, **kwargs):
        raise URLError('private-token')
    monkeypatch.setattr('active_log.instagram.urlopen', failed)
    with pytest.raises(InstagramError) as error:
        client.account()
    assert 'private-token' not in str(error.value)


def test_prepare_exports_six_jpegs(tmp_path, db):
    config = Settings(_env_file=None, instagram_media_dir=tmp_path / 'public',
                      instagram_media_base_url='https://cdn.example/cards')
    urls, caption = prepare_cards(config, db.get_post(1), None)
    assert len(urls) == 6
    assert caption
    assert all(url.endswith('.jpg') for url in urls)
    from PySide6.QtGui import QImage
    paths = list(config.instagram_media_dir.glob('*/*.jpg'))
    assert len(paths) == 6
    assert all(QImage(str(path)).size().toTuple() == (1080, 1350) for path in paths)


def test_auto_crosspost_failure_keeps_tistory_success(db, monkeypatch):
    import asyncio
    from active_log.service import AutomationService
    from unittest.mock import AsyncMock
    config = Settings(_env_file=None, instagram_auto_publish=True)
    service = AutomationService(config, db)
    monkeypatch.setattr(service, '_validated_post', lambda _: db.get_post(1))
    monkeypatch.setattr(service, 'ensure_images', lambda _: [Path('poster.png')])
    publisher = Mock()
    publisher.publish = AsyncMock(return_value='https://blog.example/1')
    monkeypatch.setattr('active_log.service.TistoryPublisher', lambda *args: publisher)
    monkeypatch.setattr(service, 'publish_instagram', AsyncMock(side_effect=InstagramError('error')))
    assert asyncio.run(service.publish_public(1)) == 'https://blog.example/1'
    assert db.get_post(1)['status'] == 'public'
    assert '인스타그램 게시 실패:' in db.get_state('last_instagram_result')


@pytest.mark.parametrize('state,expected', [('PUBLISHED','published'), ('ERROR','failed'),
                                            ('EXPIRED','failed'), ('FINISHED','unknown')])
def test_reconcile_changes_only_definitive_states(db, state, expected):
    db.claim_instagram(1, '123')
    db.update_instagram(1, '123', 'unknown', container_id='container')
    client = Client()
    client.request = Mock(return_value={'status_code': state})
    InstagramPublisher(Settings(_env_file=None), db, client).reconcile(1)
    assert db.list_instagram_publications()[0]['status'] == expected


def test_auto_crosspost_is_disabled_by_default(db, monkeypatch):
    import asyncio
    from active_log.service import AutomationService
    from unittest.mock import AsyncMock
    service = AutomationService(Settings(_env_file=None), db)
    monkeypatch.setattr(service, '_validated_post', lambda _: db.get_post(1))
    monkeypatch.setattr(service, 'ensure_images', lambda _: [])
    publisher = Mock()
    publisher.publish = AsyncMock(return_value='https://blog.example/1')
    monkeypatch.setattr('active_log.service.TistoryPublisher', lambda *args: publisher)
    crosspost = AsyncMock()
    monkeypatch.setattr(service, 'publish_instagram', crosspost)
    asyncio.run(service.publish_public(1))
    crosspost.assert_not_awaited()
