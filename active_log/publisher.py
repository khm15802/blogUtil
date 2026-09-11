import asyncio
import json
import html
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright


class TistoryPublisher:
    """Automate Tistory management with an authenticated Chrome session."""

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

    @staticmethod
    async def _fetch_view_counts(page, post_ids: list[int]) -> dict[int, int]:
        """Fetch cumulative views from authenticated Tistory statistics in small batches."""
        if not post_ids:
            return {}
        raw_counts = await page.evaluate(
            """async ids => {
                const counts = {};
                let cursor = 0;
                async function worker() {
                    while (cursor < ids.length) {
                        const id = ids[cursor++];
                        try {
                            const response = await fetch(
                                `/manage/v2/statistics/entry/base?entryId=${id}&metric=pv`,
                                {credentials: 'same-origin'}
                            );
                            if (!response.ok) continue;
                            const payload = await response.json();
                            const count = payload && payload.data && payload.data.count;
                            if (Number.isFinite(Number(count))) counts[id] = Number(count);
                        } catch (_) {
                            // A single unavailable statistic must not hide the post list.
                        }
                    }
                }
                await Promise.all(Array.from({length: Math.min(6, ids.length)}, worker));
                return counts;
            }""",
            post_ids,
        )
        return {
            int(post_id): int(count)
            for post_id, count in (raw_counts or {}).items()
            if str(post_id).isdigit()
        }

    async def publish_private(self, post: dict, image_paths: list[Path] | None = None) -> str:
        return await self.publish(post, image_paths, visibility="private")

    @staticmethod
    async def _clear_editor_content(page) -> None:
        """Remove a restored Tistory autosave before adding this post's images."""
        await page.wait_for_timeout(700)
        cleared = await page.evaluate(
            """() => {
                const editor = window.tinymce && window.tinymce.activeEditor;
                if (!editor) return false;
                editor.setContent('');
                editor.fire('input');
                editor.fire('change');
                editor.save();
                return true;
            }"""
        )
        if cleared:
            return
        editor = page.locator(".ProseMirror:visible, [contenteditable='true']:visible").last
        if await editor.count():
            await editor.evaluate(
                """el => {
                    el.innerHTML = '';
                    el.dispatchEvent(new InputEvent('input', {bubbles:true,inputType:'deleteContent'}));
                }"""
            )
            return
        raise RuntimeError("새 글 편집기의 이전 자동저장 내용을 초기화하지 못했습니다.")

    @staticmethod
    async def _set_and_verify_title(title_input, expected_title: str) -> None:
        """Set the title after autosave restoration and verify the live field value."""
        await title_input.fill(expected_title)
        await title_input.press("Tab")
        actual_title = (await title_input.input_value()).strip()
        if actual_title != expected_title:
            raise RuntimeError(
                "티스토리 편집기의 제목이 다른 글로 바뀌어 게시를 중단했습니다. "
                f"(예상: {expected_title} / 실제: {actual_title or '빈 제목'})"
            )

    @staticmethod
    async def _upload_image(page, image_path: Path) -> None:
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

    @staticmethod
    def _normalized_title(title: str) -> str:
        return re.sub(r'\W+', '', html.unescape(title)).casefold()

    async def _assert_no_duplicate(self, page, title: str) -> None:
        """Check the management list before opening a new post."""
        expected = self._normalized_title(title)
        seen_pages: set[tuple[str, ...]] = set()
        for page_number in range(1, 101):
            await page.goto(
                f'https://{self.blog_name}.tistory.com/manage/posts/?page={page_number}',
                wait_until='domcontentloaded',
            )
            if urlparse(page.url).path.rstrip('/') != '/manage/posts':
                raise RuntimeError('티스토리 기존 글 목록을 확인하지 못해 게시를 중단했습니다. 로그인을 확인하세요.')
            await page.wait_for_timeout(500)
            titles = await page.locator('.post_cont .link_cont').all_text_contents()
            if not titles:
                raise RuntimeError('기존 글 목록을 읽지 못해 중복 검사를 완료하지 못했습니다.')
            if any(self._normalized_title(value) == expected for value in titles):
                raise RuntimeError('티스토리에 같은 제목의 글이 이미 있어 중복 게시를 차단했습니다.')
            signature = tuple(titles)
            if signature in seen_pages:
                raise RuntimeError('기존 글 목록 페이지가 반복되어 중복 검사를 완료하지 못했습니다.')
            seen_pages.add(signature)
            if len(titles) < 15:
                return
        raise RuntimeError('기존 글 목록의 중복 검사 범위를 초과해 게시를 중단했습니다.')

    @staticmethod
    async def _verify_post_images(page, expected_count: int) -> None:
        state = await page.evaluate("""() => {
            const editor = window.tinymce && window.tinymce.activeEditor;
            if (!editor) return null;
            const images = Array.from(editor.getBody().querySelectorAll('img'));
            return {count: images.length, loaded: images.filter(img => img.complete && img.naturalWidth > 0).length};
        }""")
        if not state or state['count'] < expected_count or state['loaded'] < expected_count:
            raise RuntimeError('공식 포스터가 편집기에 정상 반영되지 않아 게시를 중단했습니다.')

    async def publish(self, post: dict, image_paths: list[Path] | None = None, *, visibility: str = "private") -> str:
        if visibility not in {"private", "public"}:
            raise ValueError("visibility는 private 또는 public이어야 합니다.")
        if not image_paths or any(not path.is_file() or path.stat().st_size == 0 for path in image_paths):
            raise RuntimeError('공식 포스터가 없어 게시를 보류했습니다.')
        async with async_playwright() as playwright:
            runtime_profile = self.profile_dir / "automation-runtime"
            runtime_profile.mkdir(parents=True, exist_ok=True)
            context = await playwright.chromium.launch_persistent_context(
                str(runtime_profile.resolve()), headless=self.headless, channel="chrome"
            )
            await self._restore_session(context)
            page = context.pages[0] if context.pages else await context.new_page()
            page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            try:
                await self._assert_no_duplicate(page, post['title'])
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

                # Tistory can restore an older autosave shortly after the editor opens.
                # Clear that state before setting this post's title and body.
                await self._clear_editor_content(page)
                await self._set_and_verify_title(title, post["title"])

                category_button = page.locator("#category-btn")
                await category_button.wait_for(timeout=20_000)
                await category_button.click()
                category_option = page.get_by_text(post["category"], exact=True).last
                if not await category_option.count():
                    raise RuntimeError(f"티스토리 카테고리 '{post['category']}'를 찾지 못했습니다.")
                await category_option.click()

                for image_path in image_paths or []:
                    await self._upload_image(page, image_path)

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

                # Images and mode changes may trigger a delayed autosave restore. Refuse
                # to publish unless the title still belongs to the requested post.
                await self._set_and_verify_title(title, post["title"])
                await self._verify_post_images(page, len(image_paths))
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
                public_link = published_title.locator(
                    "xpath=ancestor::li[.//a[contains(@class, 'link_cont')]][1]"
                ).locator("a.link_cont").first
                public_url = await public_link.get_attribute("href") if await public_link.count() else None
                return public_url or page.url
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

    async def list_posts(self, limit: int = 50) -> list[dict]:
        """Return posts from the real Tistory management list without changing them."""
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(self.profile_dir.resolve()), headless=self.headless, channel="chrome"
            )
            await self._restore_session(context)
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                rows: list[dict] = []
                seen_ids: set[int] = set()
                for page_number in range(1, (limit + 14) // 15 + 1):
                    await page.goto(
                        f"https://{self.blog_name}.tistory.com/manage/posts/?page={page_number}",
                        wait_until="domcontentloaded",
                    )
                    if "auth/login" in page.url:
                        raise RuntimeError("티스토리 로그인이 만료되었습니다. 채널·계정 관리에서 다시 로그인하세요.")
                    await page.wait_for_timeout(500)
                    page_rows = await page.locator("li:has(.post_cont)").evaluate_all(
                    r"""items => items.map(item => {
                        const publicLink = item.querySelector('.post_cont .link_cont');
                        const editLink = item.querySelector('a.btn_post[href*="/manage/post/"]');
                        const category = item.querySelector('.txt_cate');
                        const info = item.querySelectorAll('.post_cont .txt_info');
                        const visibility = item.querySelector('.opt_set .btn_opt .txt_ellip');
                        const match = (editLink?.getAttribute('href') || '').match(/\/manage\/post\/(\d+)/);
                        return match && publicLink ? {
                            id: Number(match[1]),
                            title: publicLink.getAttribute('title') || publicLink.textContent.trim(),
                            url: publicLink.href,
                            edit_url: new URL(editLink.getAttribute('href'), location.origin).href,
                            category: category?.textContent.trim() || '카테고리 없음',
                            author: info[0]?.textContent.trim() || '',
                            published_at: info[1]?.textContent.trim() || '',
                            visibility: visibility?.textContent.trim() || '상태 미확인'
                        } : null;
                    }).filter(Boolean)"""
                    )
                    fresh_rows = [row for row in page_rows if int(row["id"]) not in seen_ids]
                    if not fresh_rows:
                        break
                    rows.extend(fresh_rows)
                    seen_ids.update(int(row["id"]) for row in fresh_rows)
                    if len(rows) >= limit or len(page_rows) < 15:
                        break
                await self._save_session(context)
                rows.sort(
                    key=lambda row: (str(row.get("published_at", "")), int(row["id"])),
                    reverse=True,
                )
                rows = rows[:limit]
                try:
                    view_counts = await self._fetch_view_counts(
                        page, [int(row["id"]) for row in rows]
                    )
                except Exception:
                    view_counts = {}
                for row in rows:
                    row["views"] = view_counts.get(int(row["id"]))
                return rows
            finally:
                await context.close()

    async def open_post_editor(self, post_id: int) -> None:
        """Open the real Tistory editor and keep it available for manual editing."""
        if post_id < 1:
            raise ValueError("올바른 티스토리 글 ID가 필요합니다.")
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(self.profile_dir.resolve()), headless=False, channel="chrome"
            )
            await self._restore_session(context)
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                await page.goto(
                    f"https://{self.blog_name}.tistory.com/manage/post/{post_id}",
                    wait_until="domcontentloaded",
                )
                if "auth/login" in page.url:
                    raise RuntimeError("티스토리 로그인이 만료되었습니다. 다시 로그인하세요.")
                print("티스토리 편집 창을 열었습니다. 수정 작업을 마치면 브라우저를 닫으세요.")
                while context.pages:
                    await page.wait_for_timeout(1_000)
            finally:
                await self._save_session(context)
                await context.close()

    async def add_image_to_post(self, post_id: int, image_path: Path) -> None:
        """Append an official image to an existing Tistory post and save it."""
        if post_id < 1:
            raise ValueError("올바른 티스토리 글 ID가 필요합니다.")
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        async with async_playwright() as playwright:
            runtime_profile = self.profile_dir / "automation-runtime"
            runtime_profile.mkdir(parents=True, exist_ok=True)
            context = await playwright.chromium.launch_persistent_context(
                str(runtime_profile.resolve()), headless=self.headless, channel="chrome"
            )
            await self._restore_session(context)
            page = context.pages[0] if context.pages else await context.new_page()
            page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            try:
                await page.goto(
                    f"https://{self.blog_name}.tistory.com/manage/post/{post_id}",
                    wait_until="domcontentloaded",
                )
                if "auth/login" in page.url:
                    raise RuntimeError("티스토리 로그인이 만료되었습니다. 다시 로그인하세요.")
                title = page.locator(
                    "textarea[placeholder*='제목'], input[placeholder*='제목']"
                ).first
                await title.wait_for(timeout=20_000)
                original_title = (await title.input_value()).strip()
                await self._upload_image(page, image_path)
                if (await title.input_value()).strip() != original_title:
                    raise RuntimeError("이미지 추가 중 제목이 바뀌어 저장을 중단했습니다.")
                await page.get_by_role("button", name="완료").click()
                save_button = page.get_by_role("button", name="변경사항 저장")
                if not await save_button.count():
                    save_button = page.get_by_role("button", name="공개 발행")
                if not await save_button.count():
                    save_button = page.get_by_role("button", name="저장")
                await save_button.click()
                await page.wait_for_url("**/manage/posts/**", timeout=30_000)
                await page.wait_for_timeout(2_000)
                row = page.locator(f"li:has(#inpCheck{post_id})")
                await row.wait_for(timeout=20_000)
                await self._save_session(context)
            except Exception:
                try:
                    Path("output").mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path="output/tistory-edit-error.png", full_page=True)
                except Exception:
                    pass
                raise
            finally:
                await context.close()

    async def delete_post(self, post_id: int) -> None:
        """Delete a post in Tistory and verify that it disappeared from management."""
        if post_id < 1:
            raise ValueError("올바른 티스토리 글 ID가 필요합니다.")
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(self.profile_dir.resolve()), headless=self.headless, channel="chrome"
            )
            await self._restore_session(context)
            page = context.pages[0] if context.pages else await context.new_page()
            page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            try:
                await page.goto(
                    f"https://{self.blog_name}.tistory.com/manage/posts/",
                    wait_until="domcontentloaded",
                )
                if "auth/login" in page.url:
                    raise RuntimeError("티스토리 로그인이 만료되었습니다. 다시 로그인하세요.")
                row = page.locator(f"li:has(#inpCheck{post_id})")
                await row.wait_for(timeout=20_000)
                delete_link = row.get_by_text("삭제", exact=True)
                # Tistory keeps the per-row action links hidden until its menu is
                # expanded. A DOM click invokes the same handler without depending on
                # hover state, which is unreliable in headless Chrome.
                await delete_link.evaluate("element => element.click()")
                await page.wait_for_timeout(1_000)
                confirm = page.get_by_role("button", name="삭제", exact=True).last
                if await confirm.count() and await confirm.is_visible():
                    await confirm.click()
                await page.wait_for_timeout(2_000)
                await page.reload(wait_until="domcontentloaded")
                if await page.locator(f"#inpCheck{post_id}").count():
                    raise RuntimeError("티스토리에서 게시글 삭제 완료를 확인하지 못했습니다.")
                await self._save_session(context)
            finally:
                await context.close()
