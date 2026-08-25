import asyncio
import base64
from pathlib import Path

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parent


async def main() -> None:
    skin = (ROOT / "tistory_skin" / "skin.html").read_text(encoding="utf-8")
    css = (ROOT / "tistory_skin" / "style.css").read_text(encoding="utf-8")
    skin = skin.replace('id="[##_body_id_##]"', 'id="tt-body-index"')
    skin = skin.replace('<link rel="stylesheet" href="./style.css" />', f"<style>{css}</style>")
    for name in (
        "event-cheorwon-dmz-marathon-2026.png",
        "event-gongju-baekje-marathon-2026.png",
        "event-binggrae-granfondo-2026.png",
        "event-andong-maskdance-festival-2026.png",
    ):
        image_bytes = (ROOT / "active_log" / "assets" / name).read_bytes()
        uri = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")
        skin = skin.replace(f"./images/{name}", uri)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        page = await browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        await page.set_content(skin, wait_until="domcontentloaded")
        await page.evaluate("document.body.classList.add('schedule-mode')")
        await page.screenshot(path=ROOT / "output" / "event-schedule-preview.png", full_page=True)
        visible_cards = await page.locator(".schedule-card:visible").count()
        await page.get_by_role("button", name="러닝", exact=True).click()
        running_cards = await page.locator(".schedule-card:visible").count()
        assert visible_cards == 4, visible_cards
        assert running_cards == 2, running_cards
        print(f"schedule preview verified: all={visible_cards}, running={running_cards}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
