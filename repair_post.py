import asyncio
import json

from playwright.async_api import async_playwright

from active_log.config import settings
from active_log.db import Database


POST_IDS = (6, 7, 8, 9)


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
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

        for post_id in POST_IDS:
            post = db.get_post(post_id)
            await page.goto(
                f"https://{settings.blog_name}.tistory.com/manage/posts/",
                wait_until="domcontentloaded",
            )
            title_link = page.get_by_text(post["title"], exact=True).first
            await title_link.wait_for(timeout=20_000)
            row = title_link.locator("xpath=ancestor::li[1]")
            edit_href = await row.get_by_text("수정", exact=True).get_attribute("href")
            public_href = await title_link.get_attribute("href")
            await page.goto(
                f"https://{settings.blog_name}.tistory.com{edit_href}",
                wait_until="domcontentloaded",
            )
            await page.locator("textarea[placeholder*='제목'], input[placeholder*='제목']").first.wait_for(
                timeout=20_000
            )

            mode_button = page.locator("#editor-mode-layer-btn-open")
            if await mode_button.count():
                await page.locator("#editor-mode-layer-btn-open:visible").last.click()
                html_option = page.locator("span.mce-text:visible:text-is('HTML')").last
                await html_option.wait_for(timeout=10_000)
                await html_option.click()
                await page.wait_for_timeout(700)

            code_editor = page.locator(".CodeMirror:visible").first
            await code_editor.wait_for(timeout=10_000)
            existing_html = await code_editor.evaluate("el => el.CodeMirror.getValue()")
            if post["content_html"] not in existing_html:
                repaired_html = f"{existing_html}\n{post['content_html']}"
                await code_editor.evaluate(
                    """(el, value) => {
                        const cm = el.CodeMirror;
                        cm.setValue(value);
                        cm.save();
                        const input = cm.getInputField();
                        input.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText'}));
                        input.dispatchEvent(new Event('change', {bubbles: true}));
                        cm.refresh();
                    }""",
                    repaired_html,
                )
                await page.wait_for_timeout(500)
                await page.locator("button:visible").filter(has_text="HTML").last.click()
                basic_option = page.locator("span.mce-text:visible:text-is('기본모드')").last
                await basic_option.wait_for(timeout=10_000)
                await basic_option.click()
                await page.wait_for_timeout(700)
                applied = await page.evaluate(
                    """(value) => {
                        const editor = window.tinymce && window.tinymce.activeEditor;
                        if (!editor) return false;
                        editor.setContent(value);
                        editor.fire('input');
                        editor.fire('change');
                        editor.save();
                        return true;
                    }""",
                    repaired_html,
                )
                if not applied:
                    raise RuntimeError("티스토리 기본 편집기에 본문을 반영하지 못했습니다.")
                await page.wait_for_timeout(700)

            await page.get_by_role("button", name="완료").click()
            await page.wait_for_timeout(500)
            private_option = page.get_by_text("비공개", exact=True)
            if await private_option.count():
                await private_option.last.click()
            save_button = None
            for name in ("비공개 저장", "비공개 발행", "수정", "저장"):
                candidate = page.get_by_role("button", name=name, exact=True)
                if await candidate.count():
                    save_button = candidate.last
                    break
            if save_button is None:
                print("visible buttons:", await page.get_by_role("button").all_inner_texts())
                await page.screenshot(path="output/repair-save-modal.png", full_page=True)
                raise RuntimeError("수정 저장 버튼을 찾지 못했습니다.")
            await save_button.click()
            await page.wait_for_url("**/manage/posts/**", timeout=30_000)

            await page.goto(public_href, wait_until="domcontentloaded")
            body_text = await page.locator("body").inner_text()
            marker = "대회 기본 정보" if post_id in (6, 7) else "행사 기본 정보" if post_id == 8 else "축제 기본 정보"
            if marker not in body_text:
                raise RuntimeError(f"본문 저장 검증 실패: {post['title']}")
            print(f"repaired {post_id}: {post['title']}")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
