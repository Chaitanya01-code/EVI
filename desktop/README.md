# EVI Local Desktop Runtime

This directory contains the single local runtime entry point for EVI. It starts and supervises the existing FastAPI backend and React/Vite frontend, then displays that frontend in the existing PyWebView native window. It does not contain agent logic, task routing, orchestration, memory, API routes, or UI code.

The native desktop window uses PyWebView. The existing React frontend remains unchanged and is loaded from the local Vite server without a browser address bar or browser navigation controls.

## Required Dependency

Install the existing backend dependencies, including PyWebView:

```powershell
python -m pip install -r backend\requirements.txt
```

To install only the new desktop-window dependency:

```powershell
python -m pip install pywebview
```

## Startup Contract

- Backend application: `app.main:app`
- Backend working directory: `backend/`
- Backend command: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- Frontend working directory: `frontend/`
- Development frontend command: `npm run dev -- --host 127.0.0.1`
- Development frontend URL: `http://127.0.0.1:5173/`
- Backend URL: `http://127.0.0.1:8000/`
- Frontend API URL: `VITE_API_URL`, defaulting to `http://127.0.0.1:8000`
- Startup timeout: `desktop/config.json` -> `startup_timeout_seconds`
- Shutdown timeout: `desktop/config.json` -> `shutdown_timeout_seconds`

The backend loads `backend/.env`. PostgreSQL remains required through `DB_URL`; the existing backend database initialization is unchanged.

## Frontend Production Build

The existing Vite configuration uses the standard production output directory:

```text
frontend/dist/
```

Build the frontend manually from the repository root:

```powershell
Set-Location frontend
npm run build
```

This produces the static React application in `frontend/dist/` while preserving the existing chat, voice, Lab, work/task UI, routes, API calls, assets, and styling. Production API requests use `VITE_API_URL` when provided; otherwise they use the local FastAPI backend at `http://127.0.0.1:8000`.

## Development Launch

From the repository root in PowerShell:

```powershell
python desktop\run.py
```

The launcher resolves paths from the source repository location, not from the terminal's current directory. It starts the existing backend, waits for its HTTP endpoint, starts the Vite development server, waits for the frontend, creates the native EVI window, and monitors both child processes while the window is open. Closing the EVI window stops the frontend first and the backend second. `Ctrl+C` closes the window and performs the same cleanup.

The launcher uses the repository `.venv` automatically when available. Set `EVI_PYTHON` to an alternate Python executable when needed.

Expected status output is:

```text
[EVI] Starting backend...
[EVI] Backend ready: http://127.0.0.1:8000/
[EVI] Starting frontend...
[EVI] Frontend ready: http://127.0.0.1:5173/
[EVI] EVI is ready.
```

After the final status line, an `EVI` window opens with the existing React interface at `http://127.0.0.1:5173/`. The window is resizable and starts at 1280x800.

Before starting children, the launcher checks the configured backend and frontend directories and confirms that `DB_URL` is available either in the environment, `backend/.env` in source mode, or `release/.env` in frozen mode. If configuration is missing or invalid, Python/npm cannot start, a child process exits, or either URL remains unavailable, the launcher prints an explicit `[EVI] Startup failed:` message and shuts down any child process it started. On Windows, shutdown first signals the owned process group and only falls back to terminating that process tree if it does not exit.

## Future Packaged Mode

The launcher supports the production frontend runtime without packaging an executable:

```powershell
python desktop\run.py --mode packaged
```

Packaged mode expects an existing production build at `frontend/dist/index.html`, serves that static output through the existing Vite preview command, and opens the same native window. It does not build the frontend automatically, so run `npm run build` first. If the build is missing, the launcher reports the exact required command and exits without starting child processes.

The current status is:

- Development mode: FastAPI + Vite dev server + PyWebView.
- Packaged mode foundation: FastAPI + pre-built `frontend/dist` + Vite preview + PyWebView.
- Process ownership: the launcher tracks the backend and frontend child `Popen` instances and only terminates those owned processes.
- Future packaged environments: the launcher resolves its application root from the executable directory or bundled runtime directory when frozen, while source mode uses the repository location.

## Launcher Responsibilities

- Load and validate `desktop/config.json`.
- Select development or packaged frontend behavior.
- Start the existing FastAPI application as `app.main:app`.
- Start Vite development or packaged static serving for the existing frontend.
- Wait for backend and frontend HTTP readiness.
- Open the existing PyWebView window with the configured title and dimensions.
- Monitor child-process health and close the window if a child exits unexpectedly.
- Shut down the owned frontend and backend processes on window close, `Ctrl+C`, or startup failure.

## Current Limitations

- `EVI.exe` is not committed; it is created locally by the build command below.
- Windows startup/autostart has not been implemented.
- No installer has been implemented.
- PostgreSQL remains required through the existing `DB_URL` configuration.

## Windows Executable Build

The reproducible PyInstaller configuration is [EVI.spec](EVI.spec). It creates a console-enabled, one-file executable so the first executable build keeps startup diagnostics visible.

Install PyInstaller into the active EVI Python environment:

```powershell
python -m pip install pyinstaller
```

Build the frontend first:

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

Build the executable from the repository root:

```powershell
python -m PyInstaller desktop\EVI.spec --clean --noconfirm --distpath release --workpath build\pyinstaller
```

The executable is created at:

```text
release/EVI.exe
```

The executable bundles the existing FastAPI application modules, Uvicorn, PyWebView support, `desktop/config.json`, and `frontend/dist`. Frozen packaged mode does not run `npm run dev`, does not run `npm run build`, and does not require npm to serve the bundled frontend. The development workflow still uses the existing Vite dev server.

Run the executable from the repository root with:

```powershell
.\release\EVI.exe
```

For external configuration, place a `.env` file beside the executable. The launcher resolves this path from the actual executable location, not PyInstaller's temporary extraction directory:

```text
release/
|-- EVI.exe
`-- .env
```

At minimum, the external file must contain `DB_URL`. Existing API keys and runtime settings such as `GEMINI_API_KEY`, `DEEPGRAM_API_KEY`, `EVI_TTS_ENABLED`, and `EVI_TTS_RATE` may also be placed there. Secrets are not bundled into the executable and are never printed by the launcher. PostgreSQL remains external and unchanged.

In source/development mode, the existing `backend/.env` location remains supported. In frozen mode, `release/.env` takes priority and is loaded before the bundled backend/database modules initialize.

## GUI Startup Diagnostics

The windowed executable has no console. If packaged startup fails, the launcher writes a traceback to:

```text
release/EVI_startup.log
```

The log is created beside `EVI.exe` only when the packaged launcher runs. It is configured before startup, and its formatter redacts `DB_URL` and environment values identified as keys, secrets, passwords, or tokens. No `.env` file is bundled.

When frozen, the launcher starts the bundled FastAPI backend through a child mode of `EVI.exe`, serves the bundled production frontend through a child mode of `EVI.exe`, opens the existing PyWebView window, and shuts down only its owned child processes when the window closes.

This is the first windowed executable build. The final GUI application does not require a terminal window. Windows startup/autostart and an installer are not implemented.
