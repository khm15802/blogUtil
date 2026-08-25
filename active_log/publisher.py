import asyncio
import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright


class TistoryPublisher:
    """티스토리 편집기 UI 자동화. 공개 발행은 의도적으로 지원하지 않는다."""

    def __init__(self, blog_name: str, profile_dir: Path, headless: bool):
        self.blog_name = blog_name
        self.profile_dir = profile_dir
        self.headless = headless
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    @property
    def session_path(self) -> Path:
        return self.profile_dir / "tistory-session.json"

    async def _restore_session(self, context) -> None:
        if self.session_path.is_file():
            saved = json.loads(self.session_path.read_text(encoding="utf-8"))
            cookies = saved.get("cookies", [])
            if cookies:
                await context.add_cookies(cookies)

    async def _save_session(self, context) -> None:
        state = {"cookies": await context.cookies()}
        self.session_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    async def publish_private(self, post: dict, image_paths: list[Path] | None = None) -> str:
        return await self.publish(post, image_paths, visibility="private")

    async def publish(self, post: dict, image_paths: list[Path] | None = None, *, visibility: str = "private") -> str:
        if visibility not in {"private", "public"}:
            raise ValueError("visibility는 private 또는 public이어야 합니다.")
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(self.profile_dir.resolve()), headless=self.headless, channel="chrome"
            )
            await self._restore_session(context)
            page = context.pages[0] if context.pages else await context.new_page()
            page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            try:
                new_post_url = f"https://{self.blog_name}.tistory.com/manage/newpost/"
                await page.goto(new_post_url, wait_until="domcontentloaded")
                if "auth" in page.url or "login" in page.url:
                    if self.headless:
                        raise RuntimeError("티스토리 로그인이 필요합니다. 로그인 초기화 명령을 실행하세요.")
                    print("브라우저에서 로그인하면 게시를 자동으로 계속합니다.")
                    for _ in range(300):
                        await page.wait_for_timeout(1_000)
                        candidate = context.pages[-1] if context.pages else page
                        if self.blog_name in candidate.url and "auth" not in candidate.url and "login" not in candidate.url:
                            page = candidate
                            break
                    else:
                        raise RuntimeError("5분 안에 티스토리 로그인이 완료되지 않았습니다.")
                    await page.goto(new_post_url, wait_until="domcontentloaded")
                    if "auth" in page.url or "login" in page.url:
                        raise RuntimeError("로그인 후에도 티스토리 관리 화면에 접근하지 못했습니다.")

                title = page.locator("textarea[placeholder*='제목'], input[placeholder*='제목']").first
                await title.wait_for(timeout=20_000)
                await title.fill(post["title"])

                category_button = page.locator("#category-btn")
                await category_button.wait_for(timeout=20_000)
                await category_button.click()
                category_option = page.get_by_text(post["category"], exact=True).last
                if not await category_option.count():
                    raise RuntimeError(f"티스토리 카테고리 '{post['category']}'를 찾지 못했습니다.")
                await category_option.click()

                for image_path in image_paths or []:
                    file_input = page.locator("input[type='file'][accept*='image']").first
                    if not await file_input.count():
                        await page.locator("#mceu_0-open:visible").click()
                        async with page.expect_file_chooser(timeout=10_000) as chooser_info:
                            await page.get_by_text("사진", exact=True).last.click()
                        chooser = await chooser_info.value
                        await chooser.set_files(str(image_path.resolve()))
                    else:
                        await file_input.set_input_files(str(image_path.resolve()))
                    await page.wait_for_timeout(5_000)

                mode_button = page.locator("#editor-mode-layer-btn-open")
                if await mode_button.count():
                    await page.locator("#editor-mode-layer-btn-open:visible").last.click()
                    html_option = page.locator("span.mce-text:visible:text-is('HTML')").last
                    await html_option.wait_for(timeout=10_000)
                    await html_option.click()
                    await page.wait_for_timeout(700)

                code_editor = page.locator(".CodeMirror:visible").first
                if await code_editor.count():
                    existing_html = await code_editor.evaluate("el => el.CodeMirror.getValue()")
                    content_html = f"{existing_html}\n{post['content_html']}" if existing_html.strip() else post["content_html"]
                    await code_editor.evaluate(
                        """(el, value) => {
                            const cm = el.CodeMirror;
                            cm.setValue(value);
                            cm.save();
                            cm.getInputField().dispatchEvent(new Event('input', {bubbles: true}));
                            cm.getInputField().dispatchEvent(new Event('change', {bubbles: true}));
                            cm.refresh();
                        }""",
                        content_html,
                    )
                    await page.wait_for_timeout(500)
                    saved_html = await code_editor.evaluate("el => el.CodeMirror.getValue()")
                    if post["content_html"] not in saved_html:
                        raise RuntimeError("HTML 본문이 티스토리 편집기에 반영되지 않았습니다.")
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
                        content_html,
                    )
                    if not applied:
                        raise RuntimeError("티스토리 기본 편집기에 본문을 반영하지 못했습니다.")
                    await page.wait_for_timeout(700)
                else:
                    editor = page.locator(".ProseMirror:visible, [contenteditable='true']:visible, textarea:visible").last
                    if await editor.count():
                        await editor.click()
                        await editor.evaluate(
                            "(el, value) => { el.innerHTML = value; el.dispatchEvent(new InputEvent('input', {bubbles:true,inputType:'insertText'})); }",
                            post["content_html"],
                        )
                    else:
                        frame_editor = None
                        for frame in page.frames[1:]:
                            candidate = frame.locator(
                                "body[contenteditable='true'], body.mce-content-body, [contenteditable='true']"
                            ).first
                            if await candidate.count() and await candidate.is_visible():
                                frame_editor = candidate
                                break
                        if frame_editor is None:
                            raise RuntimeError("티스토리 본문 편집 영역을 찾지 못했습니다.")
                        await frame_editor.click()
                        await frame_editor.evaluate(
                            "(el, value) => { el.innerHTML = value; el.dispatchEvent(new InputEvent('input', {bubbles:true,inputType:'insertText'})); }",
                            post["content_html"],
                        )

                tag_input = page.locator("input[placeholder*='태그']").first
                if await tag_input.count():
                    for tag in json.loads(post["tags_json"]):
                        await tag_input.fill(tag)
                        await tag_input.press("Enter")

                await page.get_by_role("button", name="완료").click()
                option_label = "공개" if visibility == "public" else "비공개"
                visibility_option = page.get_by_text(option_label, exact=True)
                await visibility_option.wait_for(timeout=10_000)
                await visibility_option.click()
                button_label = "공개 발행" if visibility == "public" else "비공개 발행"
                publish_button = page.get_by_role("button", name=button_label)
                if not await publish_button.count():
                    publish_button = page.get_by_role("button", name="저장")
                await publish_button.click()
                await page.wait_for_url("**/manage/posts/**", timeout=30_000)
                await page.wait_for_timeout(2_000)
                published_title = page.get_by_text(post["title"], exact=True).first
                await published_title.wait_for(timeout=20_000)
                list_text = await page.locator("body").inner_text()
                if visibility == "private" and "비공개" not in list_text:
                    raise RuntimeError("게시글은 찾았지만 비공개 상태를 확인하지 못했습니다.")
                await self._save_session(context)
                return page.url
            except Exception:
                try:
                    Path("output").mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path="output/tistory-publish-error.png", full_page=True)
                except Exception:
                    # Diagnostic capture must never hide the original publishing error.
                    pass
                raise
            finally:
                await context.close()

    async def login_interactively(self) -> None:
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(self.profile_dir.resolve()), headless=False, channel="chrome"
            )
            await self._restore_session(context)
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(f"https://{self.blog_name}.tistory.com/manage", wait_until="domcontentloaded")
            print("브라우저에서 카카오/티스토리 로그인을 완료하세요. 관리자 화면 진입을 자동으로 확인합니다.")
            try:
                for _ in range(600):
                    await page.wait_for_timeout(1_000)
                    for candidate in reversed(context.pages):
                        parsed = urlparse(candidate.url)
                        if (
                            parsed.hostname == f"{self.blog_name}.tistory.com"
                            and parsed.path.startswith("/manage")
                        ):
                            await candidate.goto(
                                f"https://{self.blog_name}.tistory.com/manage/posts/",
                                wait_until="domcontentloaded",
                            )
                            await candidate.wait_for_timeout(3_000)
                            settled = urlparse(candidate.url)
                            if (
                                settled.hostname == f"{self.blog_name}.tistory.com"
                                and settled.path.startswith("/manage/posts")
                            ):
                                await self._save_session(context)
                                print("티스토리 관리자 로그인을 확인했습니다. 세션을 저장합니다.")
                                return
                raise RuntimeError("10분 안에 티스토리 관리자 로그인이 완료되지 않았습니다.")
            finally:
                await context.close()
