# Active Log 티스토리 자동화

## Windows 데스크톱 앱

웹 관리 화면 대신 데스크톱 콘텐츠 스튜디오를 사용할 수 있습니다.

```powershell
.\active-log-desktop.cmd
```

앱에서는 대기 글 목록, 글 작성과 수정, PC/모바일 HTML 미리보기,
티스토리 로그인 및 비공개 게시를 한 화면에서 사용할 수 있습니다.
최초 게시 전에는 상단의 `티스토리 로그인`을 눌러 카카오 로그인을 완료하세요.

미리 작성한 러닝, 자전거, 캠핑·레저, 행사·이벤트 글을 게시 대기열에 넣고 1~3일 간격으로 티스토리에 **비공개** 등록하는 Python 앱입니다. 예약 실행에는 OpenAI API를 사용하지 않습니다.

> 티스토리 Open API는 종료되었습니다. 이 프로젝트는 로그인된 Chrome 프로필과 티스토리 편집기 화면을 이용합니다. 화면 구조가 바뀌면 게시 모듈의 선택자를 조정해야 할 수 있습니다.

## 현재 안전 정책

- 생성 주기: 마지막 예약으로부터 무작위 1~3일
- 게시 순서: 대기열에 먼저 넣은 글부터 한 편씩 등록
- 공식 출처 링크가 없는 글은 대기열에 저장하지 않음
- `PUBLISH_VISIBILITY=private`가 아니면 게시 차단
- `AUTO_PUBLISH=false`가 기본값이며 실제 자동 등록 시 `true`로 변경
- 공개 발행 기능은 1차 버전에 포함하지 않음

## Windows 설치

1. Python 3.11 이상과 Google Chrome을 설치합니다.
2. PowerShell에서 프로젝트 폴더로 이동합니다.
3. 아래 명령을 순서대로 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m playwright install chromium
Copy-Item .env.example .env
```

예약 등록만 사용할 때는 `.env`의 `OPENAI_API_KEY`를 비워 두어도 됩니다. OpenAI 기능을 직접 실행하지 않는 한 API 사용료가 발생하지 않습니다.

## 최초 티스토리 로그인

```powershell
.\.venv\Scripts\active-log.exe login
```

열린 Chrome에서 로그인하고 티스토리 관리 페이지가 보이면 PowerShell로 돌아와 Enter를 누릅니다. 비밀번호는 앱이 저장하지 않으며 Chrome 전용 프로필의 로그인 세션을 사용합니다.

## 실행

```powershell
.\.venv\Scripts\active-log.exe serve
```

관리 화면: <http://127.0.0.1:8000>

게시 대기 글 등록: <http://127.0.0.1:8000/queue>

게시글 제작 화면: <http://127.0.0.1:8000/composer>

## 1단계: 게시글 데이터 → HTML

첫 번째 테스트 게시글 패키지만 바로 만들려면 다음 명령을 실행합니다.

```powershell
.\.venv\Scripts\active-log.exe sample
```

생성 결과:

```text
output/
├─ post.html
├─ post-data.json
└─ images/
```

- `post-data.json`: 글 내용, SEO, 행사, 해시태그, 이미지 슬롯 데이터
- `post.html`: 티스토리 HTML 모드에 붙여넣을 게시글
- `images/`: 다음 단계에서 선택한 이미지가 복사될 폴더

이미지 태그가 아직 연결되지 않은 슬롯에는 `ACTIVELOG_IMAGE:hero` 같은 HTML 주석과 미리보기용 안내 상자가 출력됩니다. 로컬 파일 경로를 `<img>`에 넣지 않습니다.

### 파일별 역할

- `active_log/models.py`: 게시글·SEO·행사·이미지 데이터 규격
- `active_log/templates/post.html.j2`: 860px 매거진형 공통 디자인
- `active_log/renderer.py`: 데이터 검증, HTML 렌더링, 패키지 출력
- `active_log/sample_data.py`: 첫 테스트 게시글 데이터
- `active_log/web.py`: 로컬 작성 화면과 미리보기
- `active_log/publisher.py`: 향후 티스토리 비공개 자동 등록 모듈

### 단계별 확장 계획

1. **완료:** 구조화된 게시글 데이터 입력과 HTML 생성
2. 이미지 파일 선택, 미리보기, alt와 삽입 위치 관리
3. 티스토리에서 얻은 실제 `[##_Image|..._##]` 태그 연결
4. PC·모바일 게시글 미리보기
5. HTML·JSON·이미지 패키지 생성 고도화
6. 검수된 결과의 티스토리 비공개 자동 등록

초기 검증 기간에는 `.env`를 다음과 같이 유지하세요.

```dotenv
PUBLISH_VISIBILITY=private
AUTO_PUBLISH=false
```

품질을 확인한 후 비공개 자동 등록만 켜려면 `AUTO_PUBLISH=true`로 바꿉니다. 여전히 모든 글은 비공개입니다.

## Windows 자동 시작

작업 스케줄러에서 로그인 시 다음 프로그램을 실행하도록 등록합니다.

- 프로그램: `D:\프로젝트\블로그 프로그램\blogUtil\.venv\Scripts\active-log.exe`
- 인수: `serve`
- 시작 위치: `D:\프로젝트\블로그 프로그램\blogUtil`

`사용자가 로그온할 때만 실행`으로 시작하는 편이 Chrome 로그인 세션과 호환성이 좋습니다. PC의 절전 모드는 꺼두세요.

## 운영 순서

1. `AUTO_PUBLISH=false`로 초안 품질 확인
2. 수동 버튼으로 비공개 등록 테스트
3. 선택자가 정상 동작하면 `AUTO_PUBLISH=true`
4. 비공개 글을 일정 기간 검수
5. 별도 승인 후에만 공개 게시 기능 개발
