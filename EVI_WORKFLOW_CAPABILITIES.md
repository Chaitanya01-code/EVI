# EVI Workflow, Capabilities, and Tools

## End-to-End Workflow

```text
Text or voice input
        |
        v
Frontend / API
        |
        +--> Voice: Deepgram STT
        |
        v
Intent classification
        |
        v
Task understanding
        |
        +--> Single task: TaskRouter -> Agent
        |
        +--> Multi-step task: Orchestrator -> Dependency plan -> Agents
        |
        v
Planner -> Policy -> Tool Registry -> Tool execution -> Verification
        |
        v
PostgreSQL task/conversation history
        |
        v
Final text response
        |
        +--> Voice input: optional TTS audio
```

The LLM interprets requests and produces structured intent. Deterministic tools perform operations. Agents do not directly invoke other agents; the orchestrator coordinates multi-step workflows.

## Agent Registry

The shared `AgentRegistry` contains four agents:

| Agent | Domain | Status |
| --- | --- | --- |
| `DesktopAgent` | Windows desktop operations | Implemented modular foundation |
| `BrowserAgent` | URLs, web search, page extraction | Implemented foundation |
| `CodingAgent` | Projects, files, commands, tests | Implemented safe foundation |
| `CloudAgent` | Provider abstraction and dry-run cloud workflows | Implemented dry-run foundation |

## DesktopAgent

### Application tools

- `open_app`
- `close_app`
- `restart_app`
- `list_apps`
- `find_app`

Applications are discovered from Windows Start Menu entries and available commands. Application-specific hardcoded branching is not the primary discovery mechanism.

### Window tools

- `switch_window`
- `minimize_window`
- `maximize_window`
- `resize_window`
- `move_window`

### File tools

- `open_file`
- `copy_file`
- `move_file`
- `rename_file`
- `delete_file`
- `search_file`

### Folder tools

- `create_folder`
- `open_folder`
- `rename_folder`
- `move_folder`
- `delete_folder`

### System tools

- `shutdown`
- `restart`
- `lock`
- `sleep`

Shutdown, restart, sleep, and destructive filesystem operations require confirmation or policy approval.

### Input tools

- `mouse_click`
- `mouse_move`
- `type_text`
- `press_key`

### Screen tools

- `screenshot`
- `inspect_screen`
- `find_ui_element`

### Terminal tools

- `run_command`
- `run_script`
- `get_output`

Terminal commands are classified by policy. Unsafe commands are blocked or require confirmation.

## BrowserAgent

### Implemented tools

- `open_url`
- `navigate`
- `search`
- `web_search`
- `read_page`
- `get_title`
- `get_links`

The current implementation uses standard-library HTTP and browser launching. Page extraction is bounded and does not send complete pages blindly to the LLM.

### Registered placeholders

These actions are registered but require a browser accessibility/DOM adapter before they can execute:

- `back`
- `forward`
- `refresh`
- `new_tab`
- Tab switching and closing
- DOM clicking and typing
- Select controls and forms
- Downloads
- YouTube and media controls

## CodingAgent

### Project tools

- `create_project`
- `inspect_project`
- `detect_stack`

### File tools

- `read_file`
- `create_file`
- `search_code`

### Execution and testing tools

- `run_command`
- `run_program`
- `run_script`
- `run_tests`
- `get_output` through command results

Commands return working directory, output, and exit status where available. Shell chaining, redirection, destructive commands, unsafe installs, and dangerous Git operations are restricted.

### Git and environment tools

- `git_status`
- `git_diff`
- `detect_python`
- `detect_node`

### Policy-gated or placeholder tools

- `edit_file`
- `delete_file`
- `install_dependency`
- `commit`
- `push`
- Autonomous debugging and automatic repair loops

## CloudAgent

### Provider abstraction

Cloud operations use the shared `CloudProvider` interface. Current provider modes are:

- `mock`: safe local dry-run provider
- `aws`: unconfigured provider status unless credentials and an adapter are added
- `azure`: unconfigured provider status unless credentials and an adapter are added
- `gcp`: unconfigured provider status unless credentials and an adapter are added

### Implemented foundation tools

- `inspect`
- `inspect_resources`
- `check_deployment`
- `deployment_status`
- `health`
- `deploy` in dry-run mode

### Placeholders

- `rollback`
- `terraform`
- `docker`
- `logs`
- `metrics`
- Live compute, storage, networking, IAM, and production deployment adapters

Real cloud mutation is not performed automatically.

## Multi-Agent Orchestrator

The orchestrator is located under `backend/app/orchestrator` and provides:

- Structured `MultiTask`, `TaskStep`, `AgentRequest`, `AgentResult`, and `ExecutionContext` models.
- Dependency-aware planning.
- Sequential execution for dependent steps.
- Parallel execution for independent steps.
- Structured result and variable passing between agents.
- Bounded retries.
- Dependency failure propagation and step skipping.
- Protected-action confirmation gating.
- Final plan verification.
- Safe progress events containing agent, action, step, and status.

Example workflow:

```text
Create a Python project
        |
        v
CodingAgent -> project_path
        |
        v
DesktopAgent -> open_folder(project_path)
```

Multi-agent orchestration is coordinated centrally. Agents do not call one another directly.

## Task History

The shared PostgreSQL persistence layer records overall tasks in `task_history` and orchestration steps in `task_history_steps`.

Recorded information includes:

- Task and step identifiers
- Session and input type
- Original request
- Agent and action
- Status
- Success and verification state
- Safe structured results
- Errors
- Created, started, completed, and update timestamps

No separate history database is created for individual agents.

## EVI Lab API

The Lab frontend uses the existing FastAPI application:

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
- `GET /api/lab/events` using Server-Sent Events

List endpoints support bounded pagination with `limit` and `offset`. Lab events include task and step lifecycle updates. The existing repository has no authentication middleware, so sensitive identifiers are omitted from Lab responses until authentication is added.

## Input and Response Modes

### Text

```text
Text input -> API -> Task/Agent -> Text response
```

### Voice

```text
Microphone audio -> Deepgram STT -> API -> Task/Agent -> Text response -> TTS audio
```

TTS receives only the final user-facing response. Internal plans, tool calls, prompts, and debugging output are not sent to TTS.

## Safety Boundaries

The following operations are not performed blindly:

- Computer shutdown, restart, or sleep
- Destructive file and folder deletion
- Unsafe terminal commands
- Git push and protected repository changes
- Dependency installation
- Cloud deployment and infrastructure mutation
- IAM or production configuration changes
- Sensitive browser submissions

The intended control flow is:

```text
Structured action -> Policy check -> Confirmation if required -> Tool -> Verification
```

## Current Limitations

- Full browser DOM/accessibility automation is not yet connected.
- Live cloud provider SDK adapters are not configured.
- Separate tool-execution persistence does not exist; the Lab executions endpoint therefore returns an empty list rather than invented records.
- Voice requires `DEEPGRAM_API_KEY`.
- TTS requires a working Windows speech engine and `pyttsx3`.
- PostgreSQL-backed API execution requires a valid `DB_URL` and installed `psycopg_pool`.
