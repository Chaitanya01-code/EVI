# EVI / NOVA Architecture

## System Overview

EVI/NOVA is a voice and text desktop assistant. It accepts typed messages and voice input, classifies requests, routes work to the appropriate agent, executes deterministic tools, persists task history, and returns a text response with optional text-to-speech output.

## Architecture Tree

```text
EVI / NOVA
|
+-- Frontend / Voice Client
|   +-- React/Vite frontend
|   +-- Typed chat input
|   +-- Microphone audio
|   +-- Optional spoken response
|
+-- FastAPI Backend
	+-- API Layer
	|   +-- Chat API
	|   +-- Voice API
	|   +-- Lab API
	|   +-- Work API
	|
	+-- Request Understanding
	|   +-- Working Context
	|   +-- Intent Classification
	|   +-- Inquiry / Clarification
	|   +-- Task Understanding
	|
	+-- Routing
	|   +-- Task Router
	|   +-- Agent Registry
	|   +-- Multi-Agent Orchestrator
	|       +-- Dependency Planning
	|       +-- Retry Management
	|       +-- Result Passing
	|       +-- Verification
	|
	+-- Agents
	|   +-- DesktopAgent
	|   |   +-- Planner
	|   |   +-- Desktop Tool Registry
	|   |   |   +-- Applications
	|   |   |   +-- Windows
	|   |   |   +-- Files and Folders
	|   |   |   +-- System
	|   |   |   +-- Input
	|   |   |   +-- Screen
	|   |   |   +-- Terminal
	|   |   +-- Executor
	|   |   +-- Verifier
	|   |   +-- Computer Controller
	|   |       +-- Mouse and Keyboard Actions
	|   |       +-- Screenshot Capture
	|   |       +-- Structured Results and Errors
	|   |       +-- Windows / Application Interaction
	|   |
	|   +-- BrowserAgent
	|   +-- CodingAgent
	|   +-- CloudAgent
	|
	+-- Shared Services
	|   +-- Memory Service
	|   +-- Policy / Decision Gate
	|   +-- Speech-to-Text
	|   +-- Text-to-Speech
	|   +-- LLM Router and Providers
	|
	+-- Persistence
		+-- Conversation History
		+-- Task History
		+-- Orchestration Step History
		+-- Long-Term Memories
		+-- PostgreSQL
```

```text
Frontend / Voice Client
	|
	v
FastAPI Application
	|
	+--> Speech-to-Text for voice input
	|
	v
Intent Classification
	|
	+--> Conversation / clarification / inquiry
	|
	+--> Task Understanding
		    |
		    +--> Task Router -> one Agent
		    |
		    +--> Orchestrator -> dependency-aware multi-agent workflow
				      |
				      v
			 Planner -> Policy -> Tool Registry
				      |
				      v
			     Tool Execution -> Verification
				      |
				      v
			 Task / Conversation Persistence
				      |
				      v
			      Response Generation
				      |
			 +------------+------------+
			 |                         |
		    Text response              Optional TTS
```

## Backend Layers

| Layer | Responsibility | Location |
| --- | --- | --- |
| API | HTTP, WebSocket, and Lab endpoints | `backend/app/api` |
| Core routing | Context, classification, and intent routing | `backend/app/core`, `backend/app/router` |
| Task system | Task understanding, routing, models, and lifecycle | `backend/app/task` |
| Agents | Domain-specific planning, execution, and verification | `backend/app/agents` |
| Orchestrator | Multi-step planning, dependencies, retries, and result passing | `backend/app/orchestrator` |
| Memory | Long-term memory service and schemas | `backend/app/memory` |
| Persistence | PostgreSQL connections, task history, conversations, and memories | `backend/app/database` |
| Voice | Speech-to-text and text-to-speech | `backend/app/voice` |

## Repository Folder Structure

```text
evi/
|-- .gitignore
|-- ARCHITEXTURE.md
|-- EVI_WORKFLOW_CAPABILITIES.md
|-- README.md
|-- docker-compose.yml
|
|-- backend/
|   |-- dockerfile
|   |-- requirements.txt
|   |-- phase2/
|   |   |-- __init__.py
|   |   |-- decision/
|   |   |   |-- __init__.py
|   |   |   `-- engine.py
|   |   |-- information/
|   |   |   |-- __init__.py
|   |   |   `-- resolver.py
|   |   `-- proactive/
|   |       |-- __init__.py
|   |       `-- intelligence.py
|   |-- app/
|   |   |-- main.py
|   |   |-- api/
|   |   |   |-- __init__.py
|   |   |   |-- chat.py
|   |   |   |-- lab_events.py
|   |   |   |-- lab_schemas.py
|   |   |   `-- routes/
|   |   |       `-- lab/
|   |   |           |-- __init__.py
|   |   |           `-- routes.py
|   |   |-- agents/
|   |   |   |-- conversation_agent.py
|   |   |   |-- base/
|   |   |   |   |-- __init__.py
|   |   |   |   `-- base_agent.py
|   |   |   |-- browser/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- agent.py
|   |   |   |   |-- executor.py
|   |   |   |   |-- planner.py
|   |   |   |   |-- registry.py
|   |   |   |   |-- tools.py
|   |   |   |   `-- verifier.py
|   |   |   |-- cloud/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- agent.py
|   |   |   |   |-- executor.py
|   |   |   |   |-- planner.py
|   |   |   |   |-- providers.py
|   |   |   |   |-- registry.py
|   |   |   |   `-- verifier.py
|   |   |   |-- coding/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- agent.py
|   |   |   |   |-- executor.py
|   |   |   |   |-- planner.py
|   |   |   |   |-- registry.py
|   |   |   |   |-- tools.py
|   |   |   |   `-- verifier.py
|   |   |   `-- desktop/
|   |   |       |-- __init__.py
|   |   |       |-- agent.py
|   |   |       |-- applications.py
|   |   |       |-- executor.py
|   |   |       |-- planner.py
|   |   |       |-- registry.py
|   |   |       |-- tools.py
|   |   |       |-- verifier.py
|   |   |       |-- applications/
|   |   |       |   |-- __init__.py
|   |   |       |   |-- close_app.py
|   |   |       |   |-- find_app.py
|   |   |       |   |-- list_apps.py
|   |   |       |   |-- open_app.py
|   |   |       |   `-- restart_app.py
|   |   |       |-- files/
|   |   |       |   |-- __init__.py
|   |   |       |   |-- copy_file.py
|   |   |       |   |-- delete_file.py
|   |   |       |   |-- move_file.py
|   |   |       |   |-- open_file.py
|   |   |       |   |-- rename_file.py
|   |   |       |   `-- search_file.py
|   |   |       |-- folders/
|   |   |       |   |-- __init__.py
|   |   |       |   |-- create_folder.py
|   |   |       |   |-- delete_folder.py
|   |   |       |   |-- move_folder.py
|   |   |       |   |-- open_folder.py
|   |   |       |   `-- rename_folder.py
|   |   |       |-- input/
|   |   |       |   |-- __init__.py
|   |   |       |   |-- mouse_click.py
|   |   |       |   |-- mouse_move.py
|   |   |       |   |-- press_key.py
|   |   |       |   `-- type_text.py
|   |   |       |-- screen/
|   |   |       |   |-- __init__.py
|   |   |       |   |-- find_ui_element.py
|   |   |       |   |-- inspect_screen.py
|   |   |       |   `-- screenshot.py
|   |   |       |-- system/
|   |   |       |   |-- __init__.py
|   |   |       |   |-- lock.py
|   |   |       |   |-- restart.py
|   |   |       |   |-- shutdown.py
|   |   |       |   `-- sleep.py
|   |   |       |-- terminal/
|   |   |       |   |-- __init__.py
|   |   |       |   |-- get_output.py
|   |   |       |   |-- run_command.py
|   |   |       |   `-- run_script.py
|   |   |       |-- windows/
|   |   |       |   |-- __init__.py
|   |   |       |   |-- maximize_window.py
|   |   |       |   |-- minimize_window.py
|   |   |       |   |-- move_window.py
|   |   |       |   |-- resize_window.py
|   |   |       |   |-- switch_window.py
|   |   |       |   `-- utils.py
|   |   |-- core/
|   |   |   |-- classify.py
|   |   |   `-- context.py
|   |   |-- database/
|   |   |   |-- __init__.py
|   |   |   |-- connection.py
|   |   |   |-- lab_store.py
|   |   |   |-- models.py
|   |   |   |-- orchestration_history.py
|   |   |   `-- store.py
|   |   |-- llm/
|   |   |   |-- config.py
|   |   |   |-- models.py
|   |   |   |-- providers.py
|   |   |   `-- router.py
|   |   |-- memory/
|   |   |   |-- __init__.py
|   |   |   |-- memory_service.py
|   |   |   `-- schemas.py
|   |   |-- orchestrator/
|   |   |   |-- __init__.py
|   |   |   |-- context_manager.py
|   |   |   |-- coordinator.py
|   |   |   |-- dependency_manager.py
|   |   |   |-- executor.py
|   |   |   |-- models.py
|   |   |   |-- orchestrator.py
|   |   |   |-- planner.py
|   |   |   |-- result_manager.py
|   |   |   |-- retry_manager.py
|   |   |   `-- verifier.py
|   |   |-- phase3/
|   |   |   |-- __init__.py
|   |   |   |-- evaluation/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- answer_evaluator.py
|   |   |   |   |-- completeness.py
|   |   |   |   `-- models.py
|   |   |   |-- inquiry/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- inquiry_context.py
|   |   |   |   |-- inquiry_engine.py
|   |   |   |   |-- inquiry_limits.py
|   |   |   |   |-- models.py
|   |   |   |   |-- question_generator.py
|   |   |   |   `-- question_manager.py
|   |   |   |-- orchestration/
|   |   |   |   |-- __init__.py
|   |   |   |   `-- inquiry_coordinator.py
|   |   |   |-- resolution/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- answer_resolver.py
|   |   |   |   |-- confidence.py
|   |   |   |   |-- knowledge_lookup.py
|   |   |   |   `-- models.py
|   |   |   |-- tests/
|   |   |   |   |-- test_evaluation.py
|   |   |   |   |-- test_inquiry.py
|   |   |   |   |-- test_inquiry_integration.py
|   |   |   |   |-- test_question_generation.py
|   |   |   |   |-- test_resolution.py
|   |   |   |   `-- test_user_questions.py
|   |   |   `-- user_questions/
|   |   |       |-- __init__.py
|   |   |       |-- answer_handler.py
|   |   |       |-- models.py
|   |   |       `-- question_presenter.py
|   |   |-- phase4/
|   |   |   |-- __init__.py
|   |   |   |-- computer/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- controller.py
|   |   |   |   `-- models.py
|   |   |   `-- tests/
|   |   |       `-- test_computer.py
|   |   |-- router/
|   |   |   |-- __init__.py
|   |   |   |-- intent_router.py
|   |   |   `-- schemas.py
|   |   |-- task/
|   |   |   |-- __init__.py
|   |   |   |-- task_manager.py
|   |   |   |-- task_models.py
|   |   |   |-- task_router.py
|   |   |   `-- task_understanding.py
|   |   |-- voice/
|   |   |   |-- speech_to_text.py
|   |   |   `-- text_to_speech.py
|   |   |-- work/
|   |   |   |-- __init__.py
|   |   |   |-- api.py
|   |   |   |-- context/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- confidence.py
|   |   |   |   |-- context_engine.py
|   |   |   |   |-- event_window.py
|   |   |   |   |-- inference.py
|   |   |   |   |-- models.py
|   |   |   |   `-- service.py
|   |   |   |-- events/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- base.py
|   |   |   |   |-- collector.py
|   |   |   |   |-- models.py
|   |   |   |   |-- normalizer.py
|   |   |   |   |-- repository.py
|   |   |   |   `-- sources/
|   |   |   |       |-- __init__.py
|   |   |   |       `-- nova.py
|   |   |   `-- proactive/
|   |   |       |-- __init__.py
|   |   |       |-- intelligence.py
|   |   |       `-- models.py
|   `-- tests/
|       |-- test_agent_foundations.py
|       |-- test_desktop_tools.py
|       |-- test_llm_router.py
|       |-- test_modular_desktop_tools.py
|       |-- test_orchestrator.py
|       |-- test_phase2.py
|       |-- test_phase3_phase4_api.py
|       |-- test_pipeline.py
|       |-- test_task_system.py
|       `-- test_work_context.py
|
|-- frontend/
|   |-- dockerfile
|   |-- index.html
|   |-- package.json
|   |-- package-lock.json
|   |-- vite.config.js
|   |-- public/
|   |   `-- evi_character.jpg
|   `-- src/
|       |-- App.css
|       |-- App.jsx
|       |-- main.jsx
|       |-- components/
|       |   `-- lab/
|       |-- pages/
|       |   |-- home/
|       |   `-- lab/
|       |-- router/
|       |-- services/
|       |   `-- labApi.js
|       `-- styles/
|
|-- data/
|-- infrastructure/
`-- learning_llm/
```

The `backend/app/phase4/computer` package contains the centralized low-level Computer Controller. Desktop task interpretation remains under `backend/app/agents/desktop`; routing, memory, orchestration, and persistence remain separate concerns.

## Agent Registry

The existing `AgentRegistry` selects one of the registered domain agents for a task. Agents do not directly call other agents.

```text
Task Router / Orchestrator
	    |
	    v
       Agent Registry
	    |
    +-------+-------+-------+
    |       |       |       |
 Desktop  Browser Coding  Cloud
 Agent    Agent   Agent   Agent
```

Each agent owns its planner, tools, execution path, and verification behavior. The shared task-history system records agent executions through the existing database architecture.

## Desktop Agent

The Desktop Agent decides what desktop operation is required for a structured task. It uses the existing planner, `DesktopToolRegistry`, executor, and verifier.

```text
Desktop Task
     |
     v
DesktopAgent
     |
     +--> Desktop Planner
     |
     +--> Desktop Tool Registry
     |
     +--> Tool Executor
     |
     +--> Verification
```

Desktop tools cover applications, windows, files, folders, system actions, input, screen capture, and terminal operations. Higher-level policy and confirmation remain outside the low-level controller.

## Computer Controller

The Computer Controller is the reusable low-level computer interaction service.

```text
Desktop Agent / Desktop Tool
	    |
	    v
Computer Controller
	    |
	    v
Windows / Application Interaction
```

The controller is implemented by `DesktopAutomationController` in `backend/app/phase4/computer/controller.py`.

### Responsibilities

- Execute low-level mouse and keyboard actions.
- Move, click, double-click, right-click, type, press keys, and send hotkeys.
- Scroll and drag.
- Wait for a bounded duration.
- Capture a screenshot for future inspection layers.
- Validate parameters and return structured success or failure results.
- Log requested, started, completed, and failed actions.

### Explicit boundaries

The Computer Controller executes low-level computer actions. It does not interpret intent, plan tasks, select agents, make policy decisions, confirm risky actions, or autonomously create tasks. Safety and confirmation decisions belong to the existing policy and orchestration layers.

### Action abstraction

Actions use the shared `ComputerAction` model:

```text
ComputerAction
  action_type: CLICK | DOUBLE_CLICK | RIGHT_CLICK | TYPE | KEY |
	       HOTKEY | SCROLL | MOVE | DRAG | WAIT | SCREENSHOT
  parameters: action-specific values
  timeout: bounded execution timeout
  metadata: optional non-sensitive context
```

Every execution returns a structured result with `success`, `action`, `message`, `error`, and optional `details` fields. Malformed parameters, unsupported keys, non-Windows execution, automation exceptions, and timeout violations return explicit failures instead of being silently ignored.

### Current integration

Existing low-level DesktopAgent input tools delegate to the centralized controller:

- `mouse_click`
- `mouse_move`
- `type_text`
- `press_key`

Existing semantic controller methods and API routes remain available for compatibility. Screenshot capture continues to use the existing Windows PowerShell utility and provides a file path; visual understanding and UI inspection are separate future capabilities.

## Browser Automation Boundary

BrowserAgent remains separate from Computer Controller responsibilities. It handles URL opening, bounded web search, and page extraction through its existing browser tools. DOM interaction and visual inspection are not implemented by the Computer Controller.

## Orchestration

The orchestrator coordinates multi-step work but does not replace the agents or their tools.

```text
Multi-step Request
	|
	v
Dependency-aware Plan
	|
	+--> Sequential dependent steps
	|
	+--> Parallel independent steps
	|
	v
Agent execution with bounded retries
	|
	v
Result passing, verification, and final response
```

Protected operations remain subject to the existing policy and confirmation flow. The Computer Controller does not bypass that flow.

## Persistence

PostgreSQL remains the shared persistence layer for conversation history, task history, orchestration steps, and long-term memories. No agent-specific database or duplicate memory system is introduced.

## Frontend and Lab

The React/Vite frontend communicates with the existing FastAPI application. The EVI Lab reads agent, task, conversation, memory, execution, health, and event data through `/api/lab` endpoints. Lab data is operational visibility and does not replace task routing or agent execution.

## Design Principles

- Reuse existing routers, agents, registries, services, and database layers.
- Keep interpretation and planning above deterministic tool execution.
- Keep policy and confirmation outside low-level computer interaction.
- Return structured results and explicit errors from every action boundary.
- Keep screenshots available without adding visual understanding.
- Avoid duplicate controllers, task managers, APIs, or memory systems.
