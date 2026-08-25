import asyncio
import sys

from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        await page.goto("https://active-log.tistory.com/?schedule=1", wait_until="networkidle")
        print("URL", page.url)
        print("SCHEDULE", await page.locator(".event-schedule-view:visible").count())
        images = await page.locator(".schedule-card img").evaluate_all(
            "imgs => imgs.map(img => ({src: img.src, currentSrc: img.currentSrc, width: img.naturalWidth, height: img.naturalHeight}))"
        )
        for image in images:
            print(image)
        await page.screenshot(path="output/event-schedule-live.png", full_page=True)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
