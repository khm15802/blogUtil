import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

from active_log.config import settings
from active_log.db import Database


async def main() -> None:
    db = Database(settings.database_path)
    post = db.get_post(7)
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
        await page.goto(f"https://{settings.blog_name}.tistory.com/manage/posts/", wait_until="domcontentloaded")
        title = page.get_by_text(post["title"], exact=True).first
        await title.wait_for(timeout=20_000)
        print("title html:", await title.evaluate("el => el.closest('li').outerHTML"))
        href = await title.get_attribute("href")
        await page.goto(href, wait_until="domcontentloaded")
        await page.wait_for_timeout(2_000)
        print("url:", page.url)
        print("article text:", (await page.locator("body").inner_text())[:1500])
        code_editor = page.locator(".CodeMirror:visible").first
        if await code_editor.count():
            value = await code_editor.evaluate("el => el.CodeMirror.getValue()")
            print("codemirror length:", len(value))
            print("contains body:", post["content_html"] in value)
        else:
            editors = page.locator(".ProseMirror:visible, [contenteditable='true']:visible")
            print("visible editors:", await editors.count())
            if await editors.count():
                value = await editors.last.inner_text()
                print("editor text length:", len(value))
                print(value[:500])
        Path("output").mkdir(exist_ok=True)
        await page.screenshot(path="output/inspect-event-post.png", full_page=True)
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
