import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

from active_log.config import settings


async def main() -> None:
    revisions = json.loads(Path("revised_posts.json").read_text(encoding="utf-8"))
    images = {
        7: ("https://www.endurohub.kr/storage/races/01KJ7WM8GJ9NKZFKT3SF5HFPG7.webp", "철원DMZ 국제평화마라톤 공식 행사 이미지"),
        8: ("https://tistory1.daumcdn.net/tistory/8978330/skin/images/event-gongju-baekje-marathon-2026.png", "2026 공주백제마라톤 공식 포스터"),
        9: ("https://tistory1.daumcdn.net/tistory/8978330/skin/images/event-binggrae-granfondo-2026.png", "2026 빙그레 그란폰도 공식 행사 이미지"),
        10: ("https://tistory1.daumcdn.net/tistory/8978330/skin/images/event-andong-maskdance-festival-2026.png", "2026 안동국제탈춤페스티벌 공식 포스터"),
    }
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

        for revision in revisions:
            post_id = revision["id"]
            await page.goto(
                f"https://{settings.blog_name}.tistory.com/manage/post/{post_id}",
                wait_until="domcontentloaded",
            )
            await page.locator("textarea[placeholder*='제목'], input[placeholder*='제목']").first.wait_for(
                timeout=20_000
            )
            await page.wait_for_timeout(800)

            image_url, image_alt = images[post_id]
            image_html = (
                f'<figure class="imageblock alignCenter"><img src="{image_url}" '
                f'alt="{image_alt}" loading="lazy"><figcaption>{image_alt}</figcaption></figure>'
            )
            result = await page.evaluate(
                """(body) => {
                    const editor = window.tinymce && window.tinymce.activeEditor;
                    if (!editor) return {ok: false};
                    const doc = new DOMParser().parseFromString(editor.getContent(), 'text/html');
                    const figure = doc.querySelector('figure.imageblock, figure');
                    const html = (figure ? figure.outerHTML : '') + body;
                    editor.setContent(html);
                    editor.fire('input');
                    editor.fire('change');
                    editor.save();
                    return {ok: true, hasFigure: Boolean(figure), length: html.length};
                }""",
                image_html + revision["html"],
            )
            if not result.get("ok"):
                raise RuntimeError(f"편집기 본문 반영 실패: {revision['title']}")

            await page.get_by_role("button", name="완료").click()
            await page.get_by_text("비공개", exact=True).last.wait_for(timeout=10_000)
            await page.get_by_text("비공개", exact=True).last.click()
            save = None
            for label in ("비공개 저장", "비공개 발행", "수정", "저장"):
                candidate = page.get_by_role("button", name=label, exact=True)
                if await candidate.count():
                    save = candidate.last
                    break
            if save is None:
                labels = await page.get_by_role("button").all_inner_texts()
                Path("output").mkdir(exist_ok=True)
                await page.screenshot(path=f"output/update-post-{post_id}-modal.png", full_page=True)
                raise RuntimeError(f"저장 버튼을 찾지 못했습니다: {labels}")
            await save.click()
            await page.wait_for_url("**/manage/posts/**", timeout=30_000)
            print(f"updated /{post_id}: figure={result['hasFigure']}, length={result['length']}")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
