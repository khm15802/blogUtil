# Active Log 티스토리 자동화

## Windows 및 macOS 데스크톱 앱

웹 관리 화면 대신 데스크톱 콘텐츠 스튜디오를 사용할 수 있습니다.

```powershell
.\active-log-desktop.cmd
```

macOS에서는 Finder에서 `active-log-desktop.command`를 더블클릭하거나 터미널에서 실행합니다.

```bash
./active-log-desktop.command
```

앱에서는 공식 행사 자료로 새 글 생성, 대기 글 목록, 글 수정, PC/모바일 HTML 미리보기,
티스토리 로그인 및 공개 게시를 한 화면에서 사용할 수 있습니다.
최초 게시 전에는 상단의 `티스토리 로그인`을 눌러 카카오 로그인을 완료하세요.

`새 글 작성`은 검증된 서울시 공식 행사 정보와 공식 포스터를 사용해 검토용 글을 만듭니다. OpenAI API 키나 사용료는 필요하지 않습니다.

새로 생성되는 글은 행사명·연도·일정·시간·장소·요금을 중심으로 제목과 본문을 구성하고, 행사명·장소 기반 태그를 자동으로 만듭니다. 공식 출처가 없거나 필수 품질검사를 통과하지 못한 글은 자동 게시 명령에서도 게시되지 않습니다.

검색 유입 상태는 코드만으로 확인할 수 없으므로 Google Search Console과 네이버 서치어드바이저에 블로그를 등록하고 티스토리 RSS·사이트맵의 수집 및 색인 상태를 주기적으로 확인하세요.

> 티스토리 Open API는 종료되었습니다. 이 프로젝트는 로그인된 Chrome 프로필과 티스토리 편집기 화면을 이용합니다. 화면 구조가 바뀌면 게시 모듈의 선택자를 조정해야 할 수 있습니다.

## 현재 안전 정책

- 생성 주기: 마지막 예약으로부터 무작위 1~3일
- 게시 순서: 대기열에 먼저 넣은 글부터 한 편씩 등록
- 공식 출처 링크가 없는 글은 대기열에 저장하지 않음
- `PUBLISH_VISIBILITY=private`가 아니면 게시 차단
- `AUTO_PUBLISH=false`가 기본값이며 실제 자동 등록 시 `true`로 변경
- 공개 발행 기능은 1차 버전에 포함하지 않음

## Windows 설치

Python 3.11 이상과 Google Chrome을 설치한 뒤 PowerShell에서 다음 설치 파일을 실행합니다.

```powershell
.\install-windows.ps1
```

설치가 끝나면 `active-log-desktop.cmd`를 더블클릭합니다. 수동 설치가 필요하다면 아래 명령을 사용합니다.

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

## macOS 설치

1. Python 3.11 이상과 Google Chrome을 설치합니다.
2. GitHub에서 받은 프로젝트 폴더를 엽니다.
3. `install-macos.command`를 더블클릭합니다.
4. 설치가 끝나면 `active-log-desktop.command`를 더블클릭합니다.

macOS가 처음 실행을 차단하면 해당 파일을 Control-클릭하고 `열기`를 선택하세요. 터미널에서 직접 설치할 수도 있습니다.

```bash
chmod +x install-macos.command active-log-desktop.command
./install-macos.command
./active-log-desktop.command
```

macOS에서는 `.venv`가 새로 생성되며 Windows에서 만든 `.venv`나 `.python` 폴더를 사용하지 않습니다. 티스토리 로그인 세션도 Mac에서 다시 생성해야 합니다. 현재 매일 07:20 자동 게시 예약은 Windows 작업 스케줄러에만 구성되어 있습니다.

`.env`의 `OPENAI_API_KEY`는 비워 두어도 됩니다. 데스크톱의 `새 글 작성`은 OpenAI API를 호출하지 않습니다.

서울시 공식 축제에서 신규 행사 글을 최대 3개 수집하려면 다음 명령을 실행합니다. 글은 검토 대기로만 저장되며 티스토리에 게시하지 않습니다.

```powershell
.\.venv\Scripts\active-log.exe collect --count 3
```

수집한 새 글을 차례로 공개 게시하는 예약 작업용 명령은 다음과 같습니다. 이 명령은 실제 티스토리 공개 상태를 변경합니다.

```powershell
.\.venv\Scripts\active-log.exe daily-publish --count 3
```

## 최초 티스토리 로그인

```powershell
.\.venv\Scripts\active-log.exe login
```

macOS:

```bash
.venv/bin/active-log login
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

## 인스타그램 자동 게시

크리에이터 또는 비즈니스 계정에서 공식 **Instagram API with Instagram Login**을 사용합니다. 페이스북 페이지 연결은 필요하지 않습니다. 개인 계정은 먼저 프로페셔널 계정으로 전환하세요. 비밀번호나 토큰을 채팅에 보내지 마세요.

1. Meta 개발자 앱을 만들고 Instagram Login API를 설정합니다. 본인 계정을 앱의 테스트 계정으로 추가하고 필요한 초대를 수락하세요. 앱 역할 밖의 계정을 연결하려면 Meta의 앱 검수·권한 승인 요건을 확인해야 합니다.
2. `instagram_business_basic`, `instagram_business_content_publish` 권한을 가진 해당 계정의 토큰을 발급합니다. `instagram-connect --browser`로 Meta 로그인을 시작하고 계정을 `.env`에 연결할 수 있습니다. 선택적으로 `INSTAGRAM_USER_ID`를 지정하면 다른 계정 토큰의 사용을 차단합니다. 토큰 자동 갱신은 지원하지 않으므로 만료 시 다시 연결하고 앱을 다시 시작하세요.
3. `INSTAGRAM_MEDIA_BASE_URL`은 기본으로 비워 둡니다. 이때 게시할 때마다 프로그램이 Cloudflare Quick Tunnel을 잠깐 열고, 임의 경로의 카드 JPEG만 외부에서 읽을 수 있게 제공합니다. 공식 GitHub 릴리스에서 `cloudflared`를 내려받을 때 SHA-256을 확인하고 로컬 `data/tools/`에 보관합니다. 캐러셀 처리가 끝나면 서버와 터널을 자동으로 닫습니다. Quick Tunnel은 테스트·개발용이며 가동 시간 보장이 없습니다. 안정적인 호스팅을 이미 운영한다면 `INSTAGRAM_MEDIA_DIR`를 `INSTAGRAM_MEDIA_BASE_URL` 아래에서 제공하고 주소를 설정해 Quick Tunnel을 건너뛸 수 있습니다. 관리 웹 전체를 공개하지 않습니다.
4. 앱을 다시 시작하고 **채널 연결 → 인스타그램 → 연결 확인**을 누릅니다. 이 동작은 계정 정보만 읽으며, 게시 권한과 이미지 호스팅의 정상 동작까지 보장하지는 않습니다.
5. 글 관리에서 로컬 본문이 있는 글을 선택하고 **인스타그램에 게시**를 누르면 기존 정보·공식 포스터로 카드 6장을 생성하고 설명문과 함께 실제 공개 게시합니다. PNG 원본은 유지하고 API용 JPEG를 별도로 만듭니다.
6. Windows에서 실행하려면 PowerShell에서 `.\.venv\Scripts\active-log.exe instagram-connect --browser`로 그 PC의 계정을 연결합니다. 로컬 HTTPS 인증서 생성에 OpenSSL이 필요합니다(Git for Windows를 기본 경로에 설치한 경우 자동으로 찾습니다). 토큰은 Git에 포함하지 않고 각 PC의 `.env`에 따로 보관합니다. 그런 다음 `.env`에 `INSTAGRAM_AUTO_PUBLISH=true`를 설정하세요. Windows 작업 스케줄러의 `daily-publish`와 데스크톱·웹의 티스토리 공개 게시 성공 뒤 카드 6장을 인스타그램에 이어서 게시합니다. 기존 게시글을 일괄 게시하거나 독립적인 인스타그램 예약을 생성하지 않습니다. 인스타그램 실패 시 티스토리 공개 게시 상태는 유지하고 결과를 기록합니다.

### Windows PC 설정

테스트 전에 명령별 동작을 구분하세요. `instagram-check`는 프로필 API로 계정만 확인하며 카드 생성·이미지 공개 호스팅·게시 자동 연동은 시험하지 않습니다. `instagram-publish <로컬 글 ID>`는 티스토리 글을 건드리지 않고 Instagram에 캐러셀을 실제 공개 게시합니다. 반면 `publish-next`와 `daily-publish`는 티스토리 글을 실제 공개 게시하며, `INSTAGRAM_AUTO_PUBLISH=true`이면 이어서 Instagram에도 게시합니다. 이 명령들은 테스트 모드가 아닙니다. 기존 공개 글은 자동 연동되지 않습니다.

프로젝트 폴더에서 PowerShell을 열고 최신 코드를 받은 뒤 설치를 갱신합니다. 설치 스크립트는 기존 `.env`를 덮어쓰지 않습니다.

```powershell
git pull origin main
.\install-windows.ps1
```

그 Windows PC에서 Instagram 계정을 한 번 연결하고 연결 상태를 확인합니다. 브라우저에서 사용할 Instagram 프로페셔널 계정으로 로그인하세요. 인증을 마치면 토큰이 해당 PC의 프로젝트 `.env`에만 저장됩니다.

```powershell
.\.venv\Scripts\active-log.exe instagram-connect --browser
.\.venv\Scripts\active-log.exe instagram-check
```

메모장으로 프로젝트의 `.env`를 열어 `INSTAGRAM_AUTO_PUBLISH=true`로 바꾼 뒤 저장합니다. 앱이나 예약 작업이 이미 실행 중이면 다시 시작해야 설정이 적용됩니다.

```powershell
notepad .env
```

이후부터 새 글의 티스토리 공개 게시가 성공하면 카드 6장을 Instagram에 이어서 게시합니다. 기존 공개 글은 자동으로 소급 게시되지 않습니다. Windows에서도 토큰을 Git에 올리거나 다른 사람에게 보내지 마세요. 토큰이 만료되면 같은 PC에서 `instagram-connect --browser`를 다시 실행합니다.

macOS CLI 예시(Windows는 `.venv\Scripts\active-log.exe`):

```sh
.venv/bin/active-log instagram-check
.venv/bin/active-log instagram-status
# 실제 공개 게시: 로컬 글 ID 사용
.venv/bin/active-log instagram-publish 47
```

같은 글·계정의 중복 게시를 DB에서 차단합니다. 준비 단계 실패(`failed`)는 재시도할 수 있습니다. 게시 요청 뒤 응답이 유실된 `unknown`과 실행 중 종료된 `preparing`/`publishing`은 자동 재시도하지 않습니다. `instagram-status`와 실제 인스타그램 피드를 비교해 확인하세요. 컨테이너가 남은 작업은 `instagram-reconcile <로컬 글 ID>`로 Meta의 상태를 조회할 수 있습니다. 게시 완료는 중복 차단을 유지하고, `ERROR`/`EXPIRED`일 때만 재시도를 허용합니다. 그 외 결과는 운영자가 추가 확인해야 합니다.

공개 카드 폴더에는 임의 경로가 사용되지만 해당 주소를 아는 사람은 이미지를 볼 수 있습니다. 접근 토큰·DB·`.env`를 정적 호스팅에 넣지 마세요. 공개 카드 파일은 자동 삭제하지 않으므로 Meta 이미지 수집과 게시 완료를 확인한 뒤 보관 정책에 따라 정리하세요. 백업·DB를 바꾸면 중복 방지 기록도 함께 보존해야 합니다.

공식 참고: [Instagram Login API](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login), [콘텐츠 게시](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing), [Meta 공식 Postman](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api).

### 메타 토큰 생성 팝업이 빈 화면으로 끝날 때

인증 후 `developers.facebook.com/instagram/token_generator/oauth/?code=...&state=...`의 빈 페이지가 남으면 공식 인증 코드를 직접 교환할 수 있습니다. 이 주소의 인증 코드는 1시간 유효하고 한 번만 사용할 수 있습니다. 이미 메타에서 사용한 코드이거나 만료된 경우 새 승인이 필요합니다. 빈 화면 자체만으로 메타 서비스 장애라고 단정하지 않습니다.

```sh
.venv/bin/active-log instagram-connect
```

터미널의 두 숨김 입력창에 (1) 빈 반환 화면의 전체 주소, (2) 메타 앱의 **Instagram 로그인이 포함된 API 설정 → Instagram 앱 시크릿 코드 → 표시** 값을 입력하세요. Facebook 앱의 시크릿과 혼동하지 마세요. 비밀번호·시크릿·반환 주소를 채팅으로 보내지 마세요. 명령은 공식 Meta/Instagram 서버에서 단기 토큰을 장기 토큰으로 교환하고, 프로필 조회·게시 권한 및 대상 계정을 검증한 뒤 `.env`에 토큰·계정 ID·만료일을 저장합니다. 앱 시크릿과 인증 코드는 저장하지 않습니다. 토큰은 화면에 출력하지 않습니다. 다른 기존 환경 설정은 보존합니다.

연결 후 앱을 다시 시작하고 `instagram-check`로 확인하세요. `INSTAGRAM_MEDIA_BASE_URL`을 비워 둔 경우 게시 시 임시 HTTPS 이미지 전달을 자동으로 준비합니다. 이 PC에서 GitHub 다운로드와 Cloudflare Quick Tunnel 접속이 허용되어야 합니다. `cloudflared` 실행 파일 경로를 직접 지정하려면 `.env`의 `CLOUDFLARED_PATH`에 경로를 입력하세요. Quick Tunnel은 [Cloudflare의 테스트·개발용 임시 터널](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)입니다.

공식 절차: [Instagram 비즈니스 로그인 — 코드를 토큰으로 교환](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/business-login).

### 붙여넣기 없이 브라우저로 연결

`.venv/bin/active-log instagram-connect --browser`는 이 컴퓨터의 `https://localhost:8766`에서 10분간 연결 화면을 제공합니다. Meta 앱의 Instagram 비즈니스 로그인 리디렉션 URI를 `https://localhost:8766/instagram/callback`으로 설정해야 합니다. 최초 접속의 임시 자체 서명 인증서 경고는 운영자가 직접 확인해야 합니다. 시스템 인증서 신뢰 설정은 변경하지 않습니다.

로컬 화면에 기존 메타 반환 주소와 Instagram 앱 시크릿을 입력하고 **로그인으로 연결**을 선택하면 프로필 조회·게시 권한만 요청합니다. 이번 승인의 새 코드는 메타의 토큰 생성 팝업을 거치지 않고 로컬 서버로 직접 돌아옵니다. 기존 반환 주소는 앱·대상 계정 식별에만 사용하며 해당 코드가 이미 사용됐어도 새 인증으로 연결할 수 있습니다. 시크릿은 서버 메모리에서만 사용하고 콜백 처리 후 폐기합니다. 로컬 HTTPS 인증서·키는 output/instagram-local-tls에 보관하며 만료 전까지 재사용합니다. OAuth 응답의 앱 범위 ID가 테스터 ID와 달라도 실제 사용자 이름이 active_log.daily인지 /me 조회로 확인하고 검증된 계정 ID를 저장합니다. 연결 성공 후 서버는 자동 종료됩니다. 다른 사이트의 요청·예측할 수 없는 경로와 일치하지 않는 요청·state 불일치를 차단하고 HTTP 접근 로그를 남기지 않습니다.
