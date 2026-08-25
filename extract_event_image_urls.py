import asyncio
import json
import sys

from playwright.async_api import async_playwright

from active_log.config import settings
from active_log.db import Database

sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    db = Database(settings.database_path)
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            str(settings.tistory_profile_dir.resolve()), headless=True, channel="chrome"
        )
        session_path = settings.tistory_profile_dir / "tistory-session.json"
        if session_path.is_file():
            cookies = json.loads(session_path.read_text(encoding="utf-8")).get("cookies", [])
            if cookies:
                await context.add_cookies(cookies)
        page = context.pages[0] if context.pages else await context.new_page()
        for post_id in (6, 7, 8, 9):
            post = db.get_post(post_id)
            await page.goto(
                f"https://{settings.blog_name}.tistory.com/manage/posts/",
                wait_until="domcontentloaded",
            )
            title_link = page.get_by_text(post["title"], exact=True).first
            await title_link.wait_for(timeout=20_000)
            href = await title_link.get_attribute("href")
            await page.goto(href, wait_until="domcontentloaded")
            await page.wait_for_timeout(1_500)
            images = await page.locator("#article-view img, .article-view img").evaluate_all(
                "imgs => imgs.map(img => img.currentSrc || img.src).filter(Boolean)"
            )
            print(post_id, post["title"])
            print(images[0] if images else "NO_IMAGE")
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
