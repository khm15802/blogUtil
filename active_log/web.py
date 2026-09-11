import asyncio
import html
import json
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from .config import settings
from .db import Database
from .service import AutomationService
from .models import PostData, SectionData, SeoData
from .renderer import PostRenderer
from .sample_data import running_schedule_sample


db = Database(settings.database_path)
service = AutomationService(settings, db)
scheduler = AsyncIOScheduler(timezone=settings.timezone)


def schedule_next(run_at: datetime | None = None) -> str:
    run_at = run_at or service.choose_next_run()

    async def job() -> None:
        try:
            await service.scheduled_cycle()
        finally:
            schedule_next()

    scheduler.add_job(job, "date", run_date=run_at, id="next_post", replace_existing=True)
    db.set_state("next_run_at", run_at.isoformat())
    return run_at.isoformat()


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler.start()
    if scheduler.get_job("next_post") is None:
        saved = db.get_state("next_run_at")
        run_at = datetime.fromisoformat(saved) if saved else service.choose_next_run()
        now = datetime.now(ZoneInfo(settings.timezone))
        if run_at <= now:
            run_at = now + timedelta(seconds=10)
        schedule_next(run_at)
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Active Log 자동화", lifespan=lifespan)
renderer = PostRenderer()


@app.middleware("http")
async def protect_local_writes(request: Request, call_next):
    """Reject cross-site browser requests to state-changing local endpoints."""
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        source = request.headers.get("origin") or request.headers.get("referer")
        if not source:
            return JSONResponse(status_code=403, content={"detail": "요청 출처를 확인할 수 없습니다."})
        parsed_source = urlsplit(source)
        if (parsed_source.scheme, parsed_source.netloc) != (request.url.scheme, request.url.netloc):
            return JSONResponse(status_code=403, content={"detail": "외부 페이지에서 보낸 요청은 허용되지 않습니다."})
    return await call_next(request)


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    rows = []
    for post in db.list_posts():
        tags = html.escape(", ".join(json.loads(post["tags_json"])))
        rows.append(
            f"<tr><td>{post['id']}</td><td>{html.escape(post['category'])}</td>"
            f"<td>{html.escape(post['title'])}</td>"
            f"<td>{html.escape(post['status'])}</td><td>{tags}</td>"
            f"<td><form method='post' action='/posts/{post['id']}/publish'>"
            "<button>승인 및 공개 게시</button></form></td></tr>"
        )
    return f"""<!doctype html><html lang='ko'><meta charset='utf-8'>
    <title>Active Log 자동화</title><style>
    body{{font-family:sans-serif;max-width:1200px;margin:40px auto;padding:0 20px}}
    table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:8px;text-align:left}}
    .safe{{color:#087f23;font-weight:bold}}button{{padding:8px 12px}}
    </style><h1>Active Log 자동화</h1><p><a href='/queue'>게시 대기 글 등록</a> · <a href='/composer'>HTML 제작 도구</a> · <a href='/stats'>조회수 통계</a></p>
    <p class='safe'>검토 완료 글만 수동으로 공개 게시하세요. 자동 공개는 꺼져 있습니다.</p>
    <p>대기 글: {db.count_drafts()}개 / 다음 자동 실행: {db.get_state('next_run_at') or '예약 전'} / 자동 등록: {settings.auto_publish}</p>
    <p>최근 실행 결과: {html.escape(db.get_state('last_cycle_result') or '아직 실행되지 않음')}</p>
    <table><thead><tr><th>ID</th><th>카테고리</th><th>제목</th><th>상태</th><th>태그</th><th>작업</th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table></html>"""


@app.get("/queue", response_class=HTMLResponse)
async def queue_form() -> str:
    return """<!doctype html><html lang='ko'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>게시 대기 글 등록</title><style>
    body{font-family:-apple-system,BlinkMacSystemFont,'Noto Sans KR',sans-serif;background:#f5f7f5;color:#202320;margin:0}
    main{max-width:900px;margin:36px auto;padding:0 20px}.panel{background:#fff;border:1px solid #e1e7e2;border-radius:14px;padding:28px}
    label{display:block;font-weight:700;margin:18px 0 7px}input,select,textarea{width:100%;box-sizing:border-box;padding:11px;border:1px solid #cbd5cd;border-radius:8px;font:inherit}
    textarea{min-height:120px}.html{min-height:360px;font-family:Consolas,monospace}button{margin-top:22px;padding:12px 18px;border:0;border-radius:8px;background:#218c45;color:#fff;font-weight:700;cursor:pointer}
    small{color:#677268}a{color:#18783a}</style><main><div class='panel'><p><a href='/'>← 관리 화면</a></p>
    <h1>게시 대기 글 등록</h1><p>여기에 저장한 글이 오래된 순서대로 1~3일 간격으로 티스토리에 비공개 등록됩니다.</p>
    <form method='post' action='/queue'>
    <label>제목</label><input name='title' required>
    <label>카테고리</label><select name='category'><option>러닝</option><option>자전거</option><option>캠핑·레저</option><option>행사·이벤트</option></select>
    <label>요약</label><textarea name='summary' required></textarea>
    <label>본문 HTML</label><textarea class='html' name='content_html' required></textarea>
    <label>태그 <small>쉼표로 구분</small></label><input name='tags'>
    <label>공식 출처 URL <small>한 줄에 하나</small></label><textarea name='sources' required></textarea>
    <label>이미지 식별자 <small>영문·숫자·하이픈. 비우면 자동 생성됩니다.</small></label><input name='topic_key' pattern='[a-z0-9-]*'>
    <p><small>대표 이미지는 active_log/assets/이미지식별자.jpg 또는 .png 파일로 넣어두면 자동 첨부됩니다.</small></p>
    <button type='submit'>게시 대기열에 저장</button></form></div></main></html>"""


@app.post("/queue")
async def queue_post(request: Request):
    values = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
    title = _field(values, "title")
    category = _field(values, "category")
    summary = _field(values, "summary")
    content_html = _field(values, "content_html")
    tags = [item.strip() for item in _field(values, "tags").split(",") if item.strip()]
    sources = [item.strip() for item in _field(values, "sources").splitlines() if item.strip()]
    topic_key = _field(values, "topic_key").lower()
    if not topic_key:
        topic_key = "manual-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    topic_key = re.sub(r"[^a-z0-9-]", "-", topic_key).strip("-")
    if not title or not summary or not content_html or not sources or not topic_key:
        raise HTTPException(status_code=422, detail="제목, 요약, 본문, 공식 출처를 확인하세요.")
    try:
        db.save_post({
            "topic_key": topic_key, "category": category, "title": title,
            "summary": summary, "content_html": content_html,
            "tags": tags, "sources": sources,
        })
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"대기열 저장 실패: {exc}") from exc
    return RedirectResponse("/", status_code=303)


@app.get("/composer", response_class=HTMLResponse)
async def composer() -> str:
    sample = running_schedule_sample()
    return f"""<!doctype html><html lang='ko'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>ACTIVELOG 게시글 제작</title><style>
    body{{margin:0;background:#f5f7f5;color:#202320;font-family:-apple-system,BlinkMacSystemFont,'Noto Sans KR',sans-serif}}
    main{{max-width:900px;margin:36px auto;padding:0 20px}}.panel{{background:#fff;border:1px solid #e3e8e3;border-radius:14px;padding:28px;box-shadow:0 8px 28px rgba(20,50,25,.05)}}
    h1{{margin:0 0 8px;font-size:30px}}.eyebrow{{color:#249447;font-weight:700;font-size:13px}}.desc{{color:#667066;margin:0 0 28px}}
    .grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}label{{display:block;font-size:13px;font-weight:700;margin-bottom:7px}}input,textarea{{width:100%;box-sizing:border-box;border:1px solid #ccd4cc;border-radius:8px;padding:11px 12px;font:inherit}}textarea{{min-height:130px;resize:vertical}}.wide{{grid-column:1/-1}}
    button{{margin-top:22px;border:0;border-radius:8px;background:#249447;color:#fff;font-weight:700;padding:12px 18px;cursor:pointer}}.sub{{background:#fff;color:#249447;border:1px solid #249447;margin-left:8px}}
    @media(max-width:650px){{.grid{{grid-template-columns:1fr}}.wide{{grid-column:auto}}.panel{{padding:20px}}}}
    </style><main><div class='panel'><div class='eyebrow'>ACTIVELOG CONTENT STUDIO · 1단계</div><h1>게시글 데이터 입력</h1><p class='desc'>콘텐츠 데이터와 디자인 템플릿을 분리해 티스토리용 HTML을 생성합니다.</p>
    <form method='post' action='/composer/generate'><div class='grid'>
    <div class='wide'><label for='title'>제목</label><input id='title' name='title' required value='{html.escape(sample.title)}'></div>
    <div><label for='category'>카테고리</label><input id='category' name='category' required value='{html.escape(sample.category)}'></div>
    <div><label for='subcategory'>하위 카테고리</label><input id='subcategory' name='subcategory' required value='{html.escape(sample.subcategory)}'></div>
    <div><label for='date'>작성일</label><input id='date' name='date' required value='{html.escape(sample.date)}'></div>
    <div><label for='keywords'>주요 키워드 (쉼표 구분)</label><input id='keywords' name='keywords' value='{html.escape(', '.join(sample.seo.keywords))}'></div>
    <div class='wide'><label for='summary'>요약 / 도입부</label><textarea id='summary' name='summary' required>{html.escape(sample.intro)}</textarea></div>
    <div class='wide'><label for='body'>본문 문단 (빈 줄로 구분)</label><textarea id='body' name='body' required>러닝 대회를 고를 때는 거리뿐 아니라 코스, 이동 시간, 접수 상태를 함께 확인해야 합니다.\n\n처음 참가한다면 무리한 기록보다 안전한 완주를 목표로 준비하세요.</textarea></div>
    <div class='wide'><label for='description'>SEO description</label><textarea id='description' name='description' required>{html.escape(sample.seo.description)}</textarea></div>
    </div><button type='submit'>HTML 생성하기</button><button class='sub' type='submit' formaction='/composer/sample'>전체 샘플 생성</button></form></div></main></html>"""


def _field(values: dict[str, list[str]], name: str) -> str:
    return values.get(name, [""])[0].strip()


@app.post("/composer/generate", response_class=HTMLResponse)
async def generate_from_form(request: Request) -> str:
    values = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
    paragraphs = [part.strip() for part in _field(values, "body").split("\n\n") if part.strip()]
    keywords = [item.strip() for item in _field(values, "keywords").split(",") if item.strip()]
    try:
        post = PostData(
            title=_field(values, "title"), category=_field(values, "category"),
            subcategory=_field(values, "subcategory"), date=_field(values, "date"),
            intro=_field(values, "summary"),
            notice="게시된 정보는 변경될 수 있으므로 이용 전 공식 안내를 확인하세요.",
            sections=[SectionData(id="content", title="핵심 내용", paragraphs=paragraphs)],
            hashtags=keywords,
            seo=SeoData(description=_field(values, "description"), keywords=keywords or ["ACTIVELOG"]),
        )
        renderer.export(post, Path("output"))
        return renderer.render(post) + "<p style='text-align:center'><a href='/composer'>← 제작 화면으로</a></p>"
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/composer/sample", response_class=HTMLResponse)
async def generate_full_sample() -> str:
    post = running_schedule_sample()
    renderer.export(post, Path("output"))
    return renderer.render(post) + "<p style='text-align:center'><a href='/composer'>← 제작 화면으로</a></p>"


@app.post("/posts/generate")
async def generate_post():
    try:
        await asyncio.to_thread(service.create_draft)
        return RedirectResponse("/", status_code=303)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/posts/{post_id}/publish")
async def publish_post(post_id: int):
    try:
        await service.publish_public(post_id)
        return RedirectResponse("/", status_code=303)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "visibility": settings.publish_visibility, "next_run_at": db.get_state("next_run_at")}


@app.get("/stats", response_class=HTMLResponse)
async def stats() -> str:
    rows = []
    for row in db.latest_view_stats():
        url = html.escape(str(row.get("url") or "#"), quote=True)
        rows.append(
            f"<tr><td>{html.escape(row['title'])}</td>"
            f"<td>{row['views']}</td><td>{row['delta']:+d}</td>"
            f"<td><a href='{url}' target='_blank' rel='noopener'>글 열기</a></td></tr>"
        )
    return """<!doctype html><html lang='ko'><meta charset='utf-8'>
    <meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>조회수 통계</title><style>
    body{font-family:sans-serif;max-width:1100px;margin:40px auto;padding:0 20px}
    table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:8px;text-align:left}
    </style><h1>조회수 통계</h1>
    <p><a href='/'>관리 화면</a> · <code>active-log sync-stats</code> 실행 후 최신 기록이 표시됩니다.</p>
    <table><thead><tr><th>제목</th><th>누적 조회수</th><th>이전 기록 대비</th><th>링크</th></tr></thead>
    <tbody>""" + "".join(rows) + "</tbody></table></html>"
