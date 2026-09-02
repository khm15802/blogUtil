# Active Log 프로젝트 맥락

마지막 갱신: 2026-09-02

## 목적

Active Log 티스토리 블로그용 콘텐츠를 작성·검토하고 게시 대기열로 관리하는 로컬 프로그램이다. 콘텐츠 데이터와 HTML 템플릿을 분리하며, 티스토리 게시에는 로그인된 Chrome 프로필과 Playwright를 사용한다.

## 현재 구성

- 언어/런타임: Python 3.11+
- 웹 관리 화면: FastAPI + Uvicorn (`active_log/web.py`)
- 데스크톱 화면: PySide6 (`active_log/desktop.py`)
- 저장소: SQLite (`active_log/db.py`, 기본 경로 `data/active_log.db`)
- 예약 실행: APScheduler
- 게시 자동화: Playwright (`active_log/publisher.py`)
- 콘텐츠 생성: 검증된 서울시 공식 행사 정보와 공식 포스터를 이용한 로컬 템플릿 생성
- HTML 생성: Jinja2 (`active_log/templates/post.html.j2`)
- 테스트: pytest (`tests/`)
- 티스토리 스킨: `tistory_skin/`

## 주요 진입점

- `active_log_app.py`: 데스크톱 앱 실행 진입점
- `active-log-desktop.cmd`: Windows 데스크톱 실행 스크립트
- `install-windows.ps1`: Windows 가상환경 및 의존성 설치
- `install-macos.command`: macOS 가상환경 및 의존성 설치
- `active-log-desktop.command`: macOS 데스크톱 실행 스크립트
- `active_log/main.py`: `active-log` CLI
- `active_log/web.py`: 관리 화면, 대기열, 작성 도구, 게시 엔드포인트
- `active_log/service.py`: 초안 생성, 카테고리 순환, 게시 및 예약 실행 조정
- `active_log/db.py`: 게시글과 런타임 상태 관리
- `active_log/quality.py`: 게시 전 품질 검사
- `active_log/official_generator.py`: 서울시 공식 축제 목록 수집, 템플릿 글 생성, 공식 포스터 저장

## 실행 방법

```powershell
# 데스크톱 앱
.\active-log-desktop.cmd

# 웹 관리 화면
.\.venv\Scripts\active-log.exe serve

# 테스트
.\.venv\Scripts\python.exe -m pytest

# 공식 행사 최대 3개를 검토 대기로 수집
.\.venv\Scripts\active-log.exe collect --count 3

# 공식 행사 최대 3개를 수집하고 실제 공개 게시
.\.venv\Scripts\active-log.exe daily-publish --count 3
```

웹 기본 주소는 `http://127.0.0.1:8000`이며 `/queue`, `/composer`, `/health` 경로를 제공한다.

macOS에서는 저장소 루트의 `install-macos.command`로 설치하고 `active-log-desktop.command`로 실행한다. 운영체제마다 가상환경과 티스토리 로그인 프로필을 별도로 생성한다. 07:20 자동 게시 예약은 현재 Windows 작업 스케줄러에서만 운영한다.

## 데이터와 게시 흐름

1. 데스크톱 상단의 `새 글 작성`을 누르면 검증된 공식 행사 자료로 글을 자동 생성하고 공식 포스터를 내려받는다.
2. SQLite `posts` 테이블에 `draft` 상태로 저장한다.
3. 대기 글은 ID 오름차순(FIFO)으로 선택한다.
4. 게시 직전에 원자적으로 `publishing` 상태를 선점해 중복 게시를 막는다.
5. 성공하면 `private` 또는 `public`, 실패하면 `failed` 상태를 기록한다.
6. 대표 이미지는 `active_log/assets/<topic_key>.<확장자>`, 상세 이미지는 `<topic_key>-detail*` 규칙으로 찾는다.

수동으로 빈 글을 여는 버튼은 제공하지 않는다. `새 글 작성`은 서울시 공식 축제 목록 조회·신규 행사 선택·템플릿 생성·공식 포스터 다운로드·정치 관련 검사·DB 저장·편집 화면 표시를 한 번에 수행한다. OpenAI API 키나 사용료는 필요하지 않는다. `active_log/official_generator.py`가 공식 출처와 확인일을 본문에 기록하며, 같은 공식 행사 코드는 중복 저장하지 않는다. 명령줄에서는 `collect --count 3`으로 여러 글을 검토 대기에 저장할 수 있다.

## 중요 안전 조건

- 실제 설정의 `PUBLISH_VISIBILITY`가 게시 방식과 일치해야 한다.
- `publish_private()`은 `private`, `publish_public()`은 `public` 설정에서만 작동한다.
- `AUTO_PUBLISH` 기본 의도는 꺼짐이며, 사용자가 승인하기 전 자동 게시를 켜지 않는다.
- 웹의 상태 변경 요청은 동일 출처 요청만 허용한다.
- `.env`, SQLite DB, 로그인 브라우저 프로필에는 민감하거나 개인적인 정보가 있을 수 있으므로 내용을 공유하거나 커밋하지 않는다.
- 새로 생성하는 콘텐츠는 정치·정당·선거·정치인·정치 집회 및 논쟁을 다루지 않는다. AI 지침과 `active_log/content_policy.py`의 저장 전 검사로 차단한다.
- `daily-publish`는 실제 공개 게시 명령이다. Windows 예약 작업에서는 사용자 로그인 상태에서만 실행하고 중복 인스턴스를 허용하지 않는다.
- Windows 예약 작업 `Active Log Daily Publish`는 매일 07:20 `daily-publish --count 3`을 실행한다. 놓친 시각에는 다음 로그인 후 실행하며 로그는 `output/daily-publish.log`에 기록한다.

## 알려진 상태와 확인 사항

- `active_log/config.py`와 `.env.example`의 `publish_visibility` 기본값은 현재 `public`이다.
- `scheduled_cycle()`은 게시 시 `publish_private()`을 호출하므로 `AUTO_PUBLISH=true`이면서 visibility가 `public`이면 실패한다. 자동 게시 정책을 정할 때 두 설정과 구현을 함께 정리해야 한다.
- README는 UTF-8 파일이지만 일부 Windows 콘솔 환경에서 한글이 깨져 출력될 수 있다.
- Git 기록상 현재 기준 커밋은 초기 Active Log 콘텐츠 스튜디오 구성이다. 이후 작업 상태는 `TODO.md`와 `git status`를 함께 확인한다.

## 문서 역할

- `AGENTS.md`: 모든 작업에서 지켜야 할 규칙
- `PROJECT_CONTEXT.md`: 잘 변하지 않는 구조, 정책, 결정
- `TODO.md`: 지금 진행 중인 일과 다음 우선순위
- `README.md`: 사용자를 위한 설치 및 사용법
