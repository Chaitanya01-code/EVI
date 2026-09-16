# EVI

EVI is a voice and text desktop assistant. It accepts browser microphone audio or typed messages, transcribes voice with Deepgram, classifies intent with Gemini, routes the request, stores conversation and task history in PostgreSQL, and speaks generated responses through the backend machine's Windows voice engine.

## Requirements

- Python 3.9+
- Node.js 18+
- A Windows speech voice for server-side TTS
- Deepgram API key for microphone transcription
- Gemini API key for intent classification and generated responses

## Configuration

Create `backend/.env` with local secrets. Do not commit this file:

```env
DEEPGRAM_API_KEY=your_deepgram_key
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-3.5-flash-lite
DB_URL=postgresql://user:password@localhost:5432/evi
EVI_TTS_ENABLED=true
EVI_TTS_RATE=175
```

Conversation history, task history, orchestration step history, and long-term memories use the PostgreSQL database configured by `DB_URL`. The backend creates or reuses the `users`, `conversation_history`, `task_history`, `task_history_steps`, and `memories` tables in that database.

## Run The Backend

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Set-Location backend
uvicorn app.main:app --reload --port 8000
```

The default route is `http://localhost:8000/`.

## Run The Frontend

In a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173/`.

## API Flow

- `POST /api/chat` processes typed messages.
- `WS /api/voice/listen` receives 16 kHz PCM microphone audio and forwards final transcripts through the same processing pipeline.
- `GET /` checks backend availability.

The processing flow is:

```text
Voice/Text
	-> Working Context
	-> Gemini structured intent classification
	-> Conversation, question, task, or clarification routing
	-> Task Router or Multi-Agent Orchestrator
	-> Agent planner, policy, tools, and verification
	-> PostgreSQL task/conversation persistence
	-> Response generation
	-> Optional text-to-speech
	-> Frontend response
```

Gemini returns `mode`, `intent`, `action`, `target`, `confidence`, `requires_action`, and `reason`. If Gemini or its configuration is unavailable, EVI uses a local classifier and keeps the request available as text.

## Task Agents

Task requests are understood by the existing Gemini client and converted into a structured task before execution. The task router selects one registered agent:

```text
Existing Architecture
	-> Task Understanding
	-> Task Router
	-> Agent Registry
	-> DesktopAgent | CodingAgent | CloudAgent | BrowserAgent
```

The agents use per-agent tool registries and return structured success and verification results. Desktop supports Windows application discovery and control. Browser supports URL opening, web search, and bounded page/title/link extraction using standard-library HTTP tools. Coding supports project inspection and creation, file reading/creation/search, controlled tests and commands, Git status/diff, and runtime detection. Cloud supports provider-neutral mock inspection, status, health, and dry-run deployment; live provider adapters and destructive operations remain policy-gated placeholders. The shared task-history system records all agents through the existing router.

## Multi-Agent Orchestration

Multi-step tasks are coordinated by `app.orchestrator`. The orchestrator builds a dependency-aware execution plan, routes each step through the existing `AgentRegistry`, passes structured output through an execution context, retries bounded failures, runs independent steps in parallel, and emits safe progress events in the task response. Protected operations wait for confirmation instead of bypassing agent policies. Per-step results extend the shared `task_history` store through `task_history_steps`.

## EVI Lab API

The existing Lab modal reads live backend data from `/api/lab`:

- `GET /api/lab/overview`
- `GET /api/lab/agents`
- `GET /api/lab/agents/{agent_id}`
- `GET /api/lab/agents/{agent_id}/activity`
- `GET /api/lab/tasks`
- `GET /api/lab/tasks/{task_id}`
- `GET /api/lab/tasks/{task_id}/steps`
- `GET /api/lab/conversations`
- `GET /api/lab/conversations/{conversation_id}`
- `GET /api/lab/memory`
- `GET /api/lab/executions`
- `GET /api/lab/system/health`
- `GET /api/lab/events` (Server-Sent Events)

Lists use `limit` and `offset` pagination. The event stream exposes safe task, step, and agent lifecycle events. There is currently no authentication middleware in the repository; Lab responses therefore omit raw user IDs and credential-like memory keys rather than claiming authorization that does not exist. Add the project's authentication dependency before exposing Lab endpoints beyond a trusted local deployment.

Set `EVI_CORS_ORIGINS` to a comma-separated list of allowed frontend origins. The local default allows Vite at `http://localhost:5173` and `http://127.0.0.1:5173`.

## Text-to-Speech

Server-side speech is enabled by default. Disable it with:

```env
EVI_TTS_ENABLED=false
```

Adjust the speaking speed with `EVI_TTS_RATE`. TTS runs asynchronously and does not block the chat response.

## Tests

Run the focused backend tests with:

```powershell
Set-Location backend
python -m pytest tests -v
```

The test suite covers routing, DesktopAgent tools, Browser/Coding/Cloud foundations, orchestration dependencies, retries, parallel branches, policy blocking, and result passing. To run the standard-library test discovery command instead:

```powershell
Set-Location backend
python -m unittest discover -s tests -v
```

