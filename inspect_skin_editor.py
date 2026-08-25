import asyncio
import json
import sys

from playwright.async_api import async_playwright

from active_log.config import settings

sys.stdout.reconfigure(encoding="utf-8")


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
        await page.goto(
            f"https://{settings.blog_name}.tistory.com/manage/design/skin/edit",
            wait_until="domcontentloaded",
        )
        await page.wait_for_timeout(4_000)
        edit_button = page.get_by_role("button", name="html 편집")
        print("EDIT_BUTTON", await edit_button.evaluate("el => el.outerHTML"))
        print("EDIT_PARENT", await edit_button.evaluate("el => el.parentElement.parentElement.outerHTML"))
        box = await edit_button.bounding_box()
        print("EDIT_BOX", box)
        if box:
            await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        await edit_button.focus()
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2_000)
        print("PAGES", [item.url for item in context.pages])
        page = context.pages[-1]
        print("URL", page.url)
        print("TITLE", await page.title())
        controls = await page.locator("button:visible, a:visible, input:visible").evaluate_all(
            "els => els.map(el => ({tag: el.tagName, id: el.id, text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim(), type: el.type || '', href: el.getAttribute('href') || ''})).filter(x => x.text || x.id)"
        )
        for control in controls:
            print(control)
        print("TEXTAREAS", await page.locator("textarea").count())
        print("CODEMIRRORS", await page.locator(".CodeMirror").count())
        print("FILE_INPUTS", await page.locator("input[type='file']").count())
        print("FRAMES", [(frame.name, frame.url) for frame in page.frames])
        print("EDIT_BUTTON_AFTER", await page.get_by_role("button", name="html 편집").count())
        editor_nodes = await page.locator("[class*='editor'], [id*='editor']").evaluate_all(
            "els => els.map(el => ({tag: el.tagName, id: el.id, cls: el.className, text: (el.innerText || '').trim().slice(0, 80)}))"
        )
        print("EDITOR_NODES", editor_nodes)
        await page.screenshot(path="output/skin-editor-inspect.png", full_page=True)
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
