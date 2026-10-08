# workMate V0.1

workMate는 메일·일정·개인 업무·향후 WorkMemory를 종합하여 먼저 업무를 챙기는 데스크톱 개인 AI 비서의 실행 가능한 기반입니다. V0.1은 외부 계정 없이도 Electron, React UI, FastAPI Agent, SQLite Task DB를 함께 실행할 수 있도록 Mock Provider를 기본값으로 제공합니다.

## 현재 구현 상태

- Electron 데스크톱 셸 (macOS / Windows)과 React + TypeScript 업무 대시보드
- Home, Assistant, Tasks, Activity 화면 및 Backend Offline 상태 화면
- FastAPI `GET /health`, dashboard, task 생성/완료, chat API
- 명시적 Intent Router 기반 Agent: 오늘 업무, 중요 메일, 메일 초안, 일정 등록 요청을 처리
- Mock Bizmeka Mail / Google Calendar / LLM / WorkMemory Provider 상태
- 첫 실행 시 제공되는 4개의 Mock 업무와 로컬 업무 추가/완료
- SQLite에 지속되는 Task 데이터와 repository/service 계층
- Tray 메뉴, `Cmd/Ctrl + Shift + Space` 빠른 호출 구조, native notification 확장 지점
- Action Card 모델: 메일/일정처럼 외부 상태를 바꾸는 작업은 검토 후 실행하도록 표시

메일 발송과 일정 생성은 V0.1에서 실제 실행하지 않습니다. API 연동 전에는 의도적으로 Action Card만 생성해 안전하게 유지합니다.

## Architecture

```text
Electron desktop shell
  ├─ Renderer: React + TypeScript (Vite)
  ├─ Tray + global shortcut + backend lifecycle
  └─ REST → FastAPI
              ├─ API router / Agent intent router
              ├─ Tool layer: Mail, Calendar, Task, Memory
              ├─ Provider seams: Mock LLM, future OpenAI/Bizmeka/Google/WorkMemory
              ├─ Dashboard + Task services
              └─ SQLite repository (V0.1)
```

Electron starts FastAPI automatically in development when `npm run dev` runs and terminates that child process when the app exits. Packaging Python and its dependencies inside the desktop installer is intentionally kept as a production TODO; the development lifecycle works today and the boundary is already isolated in `electron/main.ts`.

## Directory structure

```text
workMate/
├─ electron/                 # Desktop shell, preload bridge, tray and shortcut
├─ src/                      # React screens, API client and application styles
├─ backend/
│  ├─ server/api/            # HTTP endpoints and dependency composition
│  ├─ server/agent/          # Intent / tool selection orchestration
│  ├─ server/tools/          # Mail, Calendar, Task, Memory tool contracts
│  ├─ server/providers/      # LLM provider seams
│  ├─ server/services/       # Dashboard and task business logic
│  ├─ server/scheduler/      # Pure reminder planning seam
│  ├─ server/database/       # SQLite repository
│  └─ tests/
├─ .env.example
└─ package.json
```

## Why these choices

Electron + React + TypeScript preserves a shared macOS/Windows desktop codebase with native tray, notifications and global shortcuts. FastAPI is a compact, typed backend suitable for tool orchestration. Vite keeps the renderer feedback loop fast.

V0.1 uses **SQLite** rather than MariaDB: it has no separate local service, is reliable for a per-user desktop app, and makes onboarding and packaging substantially simpler. All persistence goes through `TaskRepository`, so moving to SQLAlchemy/MariaDB or a cloud database later does not require changing API, Agent, or UI code.

## Development setup

Prerequisites: Node.js 20+ and Python 3.10+.

This workspace uses the shared Python environment at `/Users/bizntech/Desktop/python/.venv`. It already contains the packages required by workMate. Do not create a second `backend/.venv` for normal development.

```bash
cp .env.example .env
npm install
# Only when the shared environment needs its dependencies refreshed:
/Users/bizntech/Desktop/python/.venv/bin/pip install -r backend/requirements.txt
```

On Windows use the equivalent shared virtual-environment path (for example `C:\\path\\to\\python\\.venv\\Scripts\\...`).

### macOS: run the desktop app

```bash
source /Users/bizntech/Desktop/python/.venv/bin/activate
npm run dev
```

This starts Vite, launches Electron, and has Electron start FastAPI on `http://127.0.0.1:8765`. Press `Cmd + Shift + Space` to show/hide workMate. Closing the main window hides it; choose **종료** in the tray menu to quit.

Vite and Electron both use `127.0.0.1:5173` during development. This explicit IPv4 binding prevents macOS `localhost` from resolving Vite to IPv6 (`::1`) while Electron attempts IPv4. To automatically open the renderer DevTools while diagnosing a development issue, run `WORKMATE_OPEN_DEVTOOLS=1 npm run dev`.

### Windows: run the desktop app

In PowerShell:

```powershell
C:\path\to\python\.venv\Scripts\Activate.ps1
npm run dev
```

The same shortcut becomes `Ctrl + Shift + Space`. If Windows has reserved it, change the registration in `electron/main.ts`. Packaging should be performed on Windows for the signed Windows installer; cross-platform native signing is not configured in V0.1.

### Run components separately

```bash
# terminal 1
source /Users/bizntech/Desktop/python/.venv/bin/activate
npm run backend:dev

# terminal 2
npm run dev:renderer
```

Open the Vite URL in a browser or start Electron with `npm run dev:electron` after the renderer is ready.

## APIs

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Backend liveness; returns `{ "status": "ok", "service": "workMate" }` |
| `GET /api/v1/dashboard` | Briefing, events, mail summaries, task list, provider states |
| `POST /api/v1/chat` | Agent response and optional confirmation-required Action Card |
| `POST /api/v1/tasks` | Create local workMate task |
| `POST /api/v1/tasks/{id}/complete` | Complete a task |

## Environment and real integrations

Copy `.env.example` to `.env`; `.env` is ignored by Git. The default provider modes are `mock`, so no credentials are needed.

To activate the real integrations, the next implementation phase needs:

- **Bizmeka:** API base URL, OAuth/API-key authentication details, permission scopes, and mail endpoint schema.
- **Google Calendar:** Google Cloud OAuth desktop-client credentials, redirect strategy, scopes, token storage policy, and selected calendar IDs.
- **LLM:** provider API key via environment/OS keychain, selected model, data-retention and enterprise policy. Do not log prompts with confidential mail content.
- **WorkMemory:** API base URL, authentication, response contract, and project/user authorization model.

No secrets are hardcoded. Sensitive content is not inserted into activity records. A real integration should keep read/search actions distinct from `SEND_MAIL`, `CREATE_EVENT`, `UPDATE_EVENT`, and `DELETE_EVENT`; the latter must stay behind a user approval flow.

## V0.2 Agent and tool calling

`POST /api/v1/chat` now runs a bounded agent loop: provider request → selected tool execution → provider synthesis. The loop permits multiple calls in a turn and stops after three tool rounds. Tool execution returns a compact trace (`tool`, risk, success, duration) to the client; it does not expose chain-of-thought, prompts, tokens, API keys, or mail bodies.

The Tool Registry is the single source of tool JSON schema, Pydantic argument validation, risk level, and executor. Available tools include today's/tomorrow's events, event search, local task list/create/complete, unread/important/search/get mail, mail-draft creation, calendar proposal, and WorkMemory search.

| Risk | Behavior |
| --- | --- |
| `READ` | Runs automatically for lookup/search. |
| `WRITE_LOCAL` | Creates or completes a local workMate task when explicitly requested. |
| `PROPOSED_EXTERNAL_WRITE` | Produces a pending-approval Action Card only; it cannot send mail or change Google Calendar. |

Conversation context is limited to the most recent eight messages per `conversation_id` in backend memory. It is separate from WorkMemory and is intentionally not persisted in V0.2.

### OpenAI setup

The default is safe offline mode:

```dotenv
WORKMATE_LLM_PROVIDER=mock
```

To use the real provider, set the following in the repository-root `.env`, then restart the backend/Electron development session:

```dotenv
WORKMATE_LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
WORKMATE_LLM_MODEL=gpt-4.1-mini
```

The provider uses the OpenAI Python SDK's Responses API with function definitions generated from the Tool Registry. With no key, or when `mock` is selected, the deterministic Mock LLM exercises the same agent/tool loop without network access. Do not add the key to source control.

In Electron development mode, the terminal prints safe execution events (provider, model, selected tools, success/failure, elapsed time). It never prints API keys, user text, prompts, tool output, or mail bodies. Set `WORKMATE_AGENT_DEBUG=1` to retain these events outside development mode.

## V0.3 Google Calendar

Calendar is now a swappable provider, selected in `.env`:

```dotenv
WORKMATE_CALENDAR_PROVIDER=mock # safe default
# WORKMATE_CALENDAR_PROVIDER=google
WORKMATE_TIMEZONE=Asia/Seoul
GOOGLE_CALENDAR_ID=primary
# GOOGLE_CALENDAR_CREDENTIALS_PATH=/absolute/path/to/google-oauth-desktop-client.json
# GOOGLE_CALENDAR_TOKEN_PATH=data/google_calendar_token.json
```

`MockCalendarProvider` preserves the offline demo. `GoogleCalendarProvider` uses the Google Calendar v3 client and the OAuth Desktop Application local-server authorization flow. It requests only `https://www.googleapis.com/auth/calendar.events`, which supports the event read/search/create/update/delete actions this app provides; it does not request broad Drive, Mail, or profile scopes.

### Google Cloud setup and first connection

1. In Google Cloud Console, enable **Google Calendar API** for the selected project.
2. Configure the OAuth consent screen, then create an OAuth client with application type **Desktop app**.
3. Download its JSON outside this repository and set its absolute path as `GOOGLE_CALENDAR_CREDENTIALS_PATH` in the root `.env`.
4. Set `WORKMATE_CALENDAR_PROVIDER=google`, restart workMate, then open **설정 → Google Calendar → Google 계정 연결**.
5. The system browser opens for sign-in and consent. After the localhost callback completes, workMate stores a refreshable token and the Dashboard uses the selected Google calendar.

The provider sends `singleEvents=true` on list/search calls, so recurring-event occurrences are returned as individual events. Google `dateTime` and all-day `date` event fields are normalized to workMate `Event` objects with `starts_at`, `ends_at`, `all_day`, `description`, `location`, `calendar_id`, and `source`. All date boundaries and event display use `Asia/Seoul` by default.

Calendar changes remain approval gated: the Agent only creates an Action Card; the renderer calls the approval endpoint only when the user presses **등록** (or **삭제**). The backend records `pending_approval → executing → completed/failed` and protects each in-memory action with a lock so a second click cannot create the same event twice. Read failures leave Task and Mail available instead of taking down the dashboard.

### Token security and disconnect behavior

V0.3 defines an `OAuthTokenStore` boundary. Its current `FileTokenStore` writes the refresh-token JSON to `backend/data/google_calendar_token.json` with user-only `0600` permissions; the file and OAuth client JSON names are ignored by Git. This is suitable for local development but not the final production vault: a packaged desktop build should provide a Keychain/Credential Manager implementation behind the same interface.

**연결 해제** deletes this device's local token only. It does not revoke the Google OAuth grant. Revoking the grant is a separate Google-account security action (or can be added as an explicit, clearly labelled future option), because it invalidates the grant rather than merely signing this desktop app out.

### Manual real-account verification

After connection, create `workMate 테스트` for today at 15:00 in Google Calendar (or Samsung Calendar synchronized with the same Google account), then ask `오늘 일정 알려줘.` Confirm it appears in Home and Assistant. Next ask `내일 오후 2시에 workMate 테스트 회의 등록해.`, approve the card, and verify the new event syncs back to Samsung Calendar. Finally ask the Assistant to find the event before proposing a time change or deletion; those changes must likewise remain pending until approval.

## Quality checks

```bash
npm run typecheck
npm run lint
npm run build
source /Users/bizntech/Desktop/python/.venv/bin/activate && npm run backend:test
```

## Roadmap

1. Bundle an embedded Python runtime/backend for production Electron installers.
2. Implement OAuth token vaulting and real Bizmeka / Google providers.
3. Add approved action execution and editable Action Cards.
4. Add OS-native scheduler delivery, startup registration, and notification preference controls.
5. Connect WorkMemory and improve Agent planning with contextual retrieval.
6. Add encrypted local data policy, audit settings, and end-to-end integration tests.
