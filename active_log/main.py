import argparse
import asyncio
from pathlib import Path

import uvicorn

from .config import settings
from .publisher import TistoryPublisher
from .db import Database
from .service import AutomationService
from .renderer import PostRenderer
from .sample_data import running_schedule_sample


def run() -> None:
    parser = argparse.ArgumentParser(description="Active Log 티스토리 자동화")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("serve", help="관리 화면과 스케줄러 실행")
    subparsers.add_parser("login", help="티스토리 로그인 세션 초기화")
    subparsers.add_parser("sample", help="첫 번째 테스트 게시글 패키지 생성")
    subparsers.add_parser("publish-next", help="검토를 마친 대기열의 첫 글을 티스토리에 공개 등록")
    args = parser.parse_args()

    if args.command == "login":
        publisher = TistoryPublisher(settings.blog_name, settings.tistory_profile_dir, headless=False)
        asyncio.run(publisher.login_interactively())
        return
    if args.command == "sample":
        path = PostRenderer().export(running_schedule_sample(), Path("output"))
        print(f"생성 완료: {path.resolve()}")
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
    uvicorn.run("active_log.web:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
