import argparse
import asyncio
from datetime import datetime
from pathlib import Path

import uvicorn

from .config import settings
from .publisher import TistoryPublisher
from .db import Database
from .service import AutomationService
from .renderer import PostRenderer
from .sample_data import running_schedule_sample
from .official_generator import DAILY_CATEGORIES


def run() -> None:
    parser = argparse.ArgumentParser(description="Active Log 티스토리 자동화")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("serve", help="관리 화면과 스케줄러 실행")
    subparsers.add_parser("login", help="티스토리 로그인 세션 초기화")
    edit_parser = subparsers.add_parser("edit-post", help="티스토리 게시글 수정 창 열기")
    edit_parser.add_argument("post_id", type=int)
    subparsers.add_parser("sample", help="첫 번째 테스트 게시글 패키지 생성")
    collect_parser = subparsers.add_parser("collect", help="서울시 공식 행사 글을 검토 대기로 수집")
    collect_parser.add_argument("--count", type=int, default=3, choices=range(1, 11), metavar="1-10")
    daily_parser = subparsers.add_parser(
        "daily-publish", help="공식 행사 글을 수집하고 차례로 공개 게시"
    )
    daily_parser.add_argument("--count", type=int, default=3, choices=range(1, 11), metavar="1-10")
    subparsers.add_parser("publish-next", help="검토를 마친 대기열의 첫 글을 티스토리에 공개 등록")
    stats_parser = subparsers.add_parser("sync-stats", help="공개 글 조회수를 기록")
    stats_parser.add_argument("--limit", type=int, default=50, choices=range(1, 201), metavar="1-200")
    subparsers.add_parser("instagram-check", help="환경 설정의 인스타그램 계정 연결 확인")
    instagram_parser = subparsers.add_parser("instagram-publish", help="선택 글의 카드 6장을 인스타그램에 공개 게시")
    instagram_parser.add_argument("post_id", type=int)
    subparsers.add_parser("instagram-status", help="인스타그램 게시 이력 확인")
    reconcile_parser = subparsers.add_parser("instagram-reconcile", help="불확실한 게시 결과를 Meta에서 조회해 복구")
    reconcile_parser.add_argument("post_id", type=int)
    connect_parser = subparsers.add_parser("instagram-connect", help="메타 반환 주소와 앱 시크릿으로 토큰을 안전하게 연결")
    connect_parser.add_argument("--browser", action="store_true", help="터미널 입력 대신 로컬 브라우저 연결 화면 실행")
    args = parser.parse_args()

    if args.command == "instagram-connect":
        if args.browser:
            from .instagram_auth import serve_connection
            serve_connection()
            return
        from getpass import getpass
        from .instagram_auth import connect_from_callback, parse_callback
        from .instagram import InstagramError
        print("빈 메타 반환 화면의 주소 전체와 Instagram 앱 시크릿을 준비하세요. 입력값은 화면에 표시되지 않습니다.")
        callback_url = getpass("메타 반환 주소 전체: ")
        try:
            parse_callback(callback_url)
            app_secret = getpass("Instagram 앱 시크릿: ")
            print(connect_from_callback(callback_url, app_secret))
        except InstagramError as exc:
            print(str(exc))
            raise SystemExit(1) from None
        return

    if args.command == "instagram-reconcile":
        from .instagram import InstagramPublisher
        print(InstagramPublisher(settings, Database(settings.database_path)).reconcile(args.post_id))
        return

    if args.command == "instagram-check":
        from .instagram import InstagramClient
        account = InstagramClient(settings).account()
        print(f"인스타그램 연결 확인: @{account['username']} (ID: {account['id']})")
        return
    if args.command == "instagram-status":
        for row in Database(settings.database_path).list_instagram_publications():
            print(f"글 {row['post_id']} / 계정 {row['account_id']} / {row['status']} / 미디어 {row['media_id'] or '—'}")
        return
    if args.command == "instagram-publish":
        db = Database(settings.database_path)
        print(asyncio.run(AutomationService(settings, db).publish_instagram(args.post_id)))
        return

    if args.command == "login":
        publisher = TistoryPublisher(settings.blog_name, settings.tistory_profile_dir, headless=False)
        asyncio.run(publisher.login_interactively())
        return
    if args.command == "edit-post":
        publisher = TistoryPublisher(settings.blog_name, settings.tistory_profile_dir, headless=False)
        asyncio.run(publisher.open_post_editor(args.post_id))
        return
    if args.command == "sample":
        path = PostRenderer().export(running_schedule_sample(), Path("output"))
        print(f"생성 완료: {path.resolve()}")
        return
    if args.command == "collect":
        db = Database(settings.database_path)
        post_ids = AutomationService(settings, db).collect_drafts(args.count)
        if post_ids:
            print(f"검토 대기 글 {len(post_ids)}개 저장 완료: {', '.join(map(str, post_ids))}")
        else:
            print("새로 수집할 공식 행사가 없습니다.")
        return
    if args.command == "daily-publish":
        log_path = Path("output/daily-publish.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)

        def log(message: str) -> None:
            line = f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {message}"
            print(line)
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")

        db = Database(settings.database_path)
        service = AutomationService(settings, db)
        post_ids: list[int] = []
        daily_categories = DAILY_CATEGORIES
        for index in range(args.count):
            category = daily_categories[index % len(daily_categories)]
            created = service.collect_drafts(1, category=category)
            if created:
                post_ids.extend(created)
        log(f"공식 행사 글 {len(post_ids)}개 수집: {post_ids or '없음'}")
        failures = 0
        instagram_failures = 0
        for post_id in post_ids:
            try:
                url = asyncio.run(service.publish_public(post_id))
                log(f"글 {post_id} 공개 게시 완료: {url}")
                if settings.instagram_auto_publish:
                    instagram_result = db.get_state("last_instagram_result") or f"글 {post_id} 인스타그램 결과 없음"
                    log(instagram_result)
                    if "인스타그램 게시 실패:" in instagram_result:
                        instagram_failures += 1
            except Exception as exc:
                failures += 1
                log(f"글 {post_id} 공개 게시 실패: {exc}")
        if failures or instagram_failures:
            raise SystemExit(1)
        return
    if args.command == "publish-next":
        db = Database(settings.database_path)
        post = db.get_next_draft()
        if not post:
            print("대기 중인 글이 없습니다.")
            return
        service = AutomationService(settings, db)
        url = asyncio.run(service.publish_public(int(post["id"])))
        print(f"공개 등록 완료: {url}")
        return
    if args.command == "sync-stats":
        db = Database(settings.database_path)
        count = asyncio.run(AutomationService(settings, db).sync_view_counts(args.limit))
        print(f"조회수 기록 완료: {count}개")
        return
    uvicorn.run("active_log.web:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
