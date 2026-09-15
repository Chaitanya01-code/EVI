# EVI

EVI is a voice and text desktop assistant. It accepts browser microphone audio or typed messages, transcribes voice with Deepgram, classifies intent with Gemini, routes the request, stores conversation history in SQLite, and speaks generated responses through the backend machine's Windows voice engine.

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
EVI_TTS_ENABLED=true
EVI_TTS_RATE=175
```

Conversation history and long-term memories use the PostgreSQL database configured by `DB_URL`. The backend creates or reuses the `users`, `conversation_history`, and `memories` tables in that database.

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
	-> Response generation
	-> Async SQLite persistence
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

The Desktop Agent currently supports only opening Visual Studio Code and verifies that `Code.exe` is running. Coding, Cloud, and Browser agents accept structured tasks and return safe not-enabled-yet results; they do not execute real operations yet. New agents can be added by registering a `BaseAgent` implementation in the registry.

## Text-to-Speech

Server-side speech is enabled by default. Disable it with:

```env
EVI_TTS_ENABLED=false
```

Adjust the speaking speed with `EVI_TTS_RATE`. TTS runs asynchronously and does not block the chat response.

## Tests

Run the backend pipeline tests with:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

