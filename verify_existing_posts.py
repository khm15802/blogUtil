import asyncio
import json

from playwright.async_api import async_playwright

from active_log.config import settings


async def main() -> None:
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
        await page.goto(f"https://{settings.blog_name}.tistory.com/", wait_until="domcontentloaded")
        for image in await page.locator("main img").evaluate_all(
            "els => els.map(el => ({src: el.currentSrc || el.src, alt: el.alt})).filter(x => x.alt && /(철원|공주|빙그레|안동)/.test(x.alt))"
        ):
            print(f"MAIN_IMAGE {image['alt']} => {image['src']}")
        for post_id in (7, 8, 9, 10):
            await page.goto(f"https://{settings.blog_name}.tistory.com/{post_id}", wait_until="domcontentloaded")
            article = page.locator("#article-view")
            await article.wait_for(timeout=20_000)
            text = await article.inner_text()
            images = await article.locator("img").count()
            official_links = await article.locator("a[target='_blank']").count()
            print(f"/{post_id}: text={len(text)}, images={images}, official_links={official_links}")
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
