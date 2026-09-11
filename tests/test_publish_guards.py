import asyncio
from pathlib import Path

import pytest

from active_log.config import Settings
from active_log.db import Database
from active_log.publisher import TistoryPublisher
from active_log.service import AutomationService


def test_missing_poster_blocks_before_claim_or_browser(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = Database(tmp_path / 'test.db')
    post = dict(topic_key='no-poster', category='러닝', title='대회', summary='', content_html='', tags=[], sources=[])
    post_id = db.save_post(post)
    service = AutomationService(Settings(publish_visibility='public'), db)
    monkeypatch.setattr(service, '_validated_post', lambda _: db.get_post(post_id))
    monkeypatch.setattr(db, 'claim_post_for_publish', lambda _: pytest.fail('missing poster must not be claimed'))
    with pytest.raises(RuntimeError, match='공식 포스터'):
        asyncio.run(service.publish_public(post_id))
    assert db.get_post(post_id)['status'] == 'draft'


def test_existing_official_poster_is_reused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / 'active_log/assets'
    directory.mkdir(parents=True)
    poster = directory / 'official-event.png'
    poster.write_bytes(b'official-image')
    service = AutomationService(Settings(), Database(tmp_path / 'test.db'))
    monkeypatch.setattr('active_log.service.download_official_poster', lambda *_: pytest.fail('must reuse poster'))
    assert service.ensure_images({'topic_key': 'official-event'}) == [Path('active_log/assets/official-event.png')]


def test_known_official_poster_is_downloaded_for_old_draft(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('active_log.service.OFFICIAL_EVENTS', [{'topic_key': 'official-event', 'poster_url': 'https://example.com/poster.png'}])
    called = []
    def download(event, directory):
        called.append(event['poster_url'])
        directory.mkdir(parents=True)
        (directory / 'official-event.png').write_bytes(b'official-image')
    monkeypatch.setattr('active_log.service.download_official_poster', download)
    service = AutomationService(Settings(), Database(tmp_path / 'test.db'))
    assert service.ensure_images({'topic_key': 'official-event'})
    assert called == ['https://example.com/poster.png']


def test_direct_publisher_refuses_imageless_post(tmp_path):
    publisher = TistoryPublisher('example', tmp_path, True)
    with pytest.raises(RuntimeError, match='공식 포스터'):
        asyncio.run(publisher.publish({'title': 'test'}, []))


class ListPage:
    def __init__(self, pages, redirected=False):
        self.pages = pages
        self.redirected = redirected
        self.visited = 0

    async def goto(self, url, **_kwargs):
        self.url = 'https://example.tistory.com/auth/login' if self.redirected else url
        self.visited += 1

    async def wait_for_timeout(self, _ms):
        pass

    def locator(self, _selector):
        return self

    async def all_text_contents(self):
        return self.pages[self.visited - 1]


def test_duplicate_is_detected_beyond_first_page(tmp_path):
    page = ListPage([[f'other {n}' for n in range(15)], ['고카프 PART 1 일정&middot;시간']])
    publisher = TistoryPublisher('example', tmp_path, True)
    with pytest.raises(RuntimeError, match='중복 게시'):
        asyncio.run(publisher._assert_no_duplicate(page, '고카프 PART 1 일정·시간'))
    assert page.visited == 2


def test_different_gocaf_part_is_not_duplicate(tmp_path):
    page = ListPage([['고카프 PART 1']])
    asyncio.run(TistoryPublisher('example', tmp_path, True)._assert_no_duplicate(page, '고카프 PART 2'))


@pytest.mark.parametrize('pages,redirected', [([[]], False), ([['post']], True)])
def test_unreadable_list_blocks_publication(tmp_path, pages, redirected):
    with pytest.raises(RuntimeError):
        asyncio.run(TistoryPublisher('example', tmp_path, True)._assert_no_duplicate(ListPage(pages, redirected), 'new'))


@pytest.mark.parametrize('state', [None, {'count': 0, 'loaded': 0}, {'count': 1, 'loaded': 0}])
def test_failed_upload_blocks_publication(state):
    class Page:
        async def evaluate(self, _script):
            return state
    with pytest.raises(RuntimeError, match='정상 반영'):
        asyncio.run(TistoryPublisher._verify_post_images(Page(), 1))


def test_loaded_poster_passes_verification():
    class Page:
        async def evaluate(self, _script):
            return {'count': 1, 'loaded': 1}
    asyncio.run(TistoryPublisher._verify_post_images(Page(), 1))


def test_all_known_events_excluded_from_collection(tmp_path):
    db = Database(tmp_path / 'test.db')
    for n in range(102):
        db.save_post(dict(topic_key=f'event-{n}', category='러닝', title='대회', summary='', content_html='', tags=[], sources=[]))
    assert 'event-0' in db.recent_topic_keys()
    assert len(db.recent_topic_keys()) == 102
    assert len(db.recent_topic_keys(limit=10)) == 10
