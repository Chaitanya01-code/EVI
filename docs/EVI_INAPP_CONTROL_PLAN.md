# EVI Universal Windows Application Control Plan

## Design goal

EVI should act inside arbitrary Windows applications through one capability-driven control loop, not application-specific code. It should prefer deterministic interfaces, observe the result of each action, fall back when a capability is unavailable, and stop clearly when confidence or safety is inadequate. App-specific knowledge is optional data hints, never branches or custom executable logic.

## 1. Current state

| Capability | What exists | Current limitation |
| --- | --- | --- |
| Mouse and keyboard input | `backend/app/phase4/computer/controller.py` implements mouse move/click/double-click/right-click, drag, scroll, Unicode typing, keys, hotkeys, wait, and screenshot. `backend/app/agents/desktop/input/` exposes basic tools through the controller. | These are coordinate/focused-input primitives, not semantic app control. There is no global kill switch, active-window targeting, visible control indicator, password-field protection, or general policy check at the low-level controller boundary. |
| Window discovery | `backend/app/agents/desktop/windows/utils.py` enumerates visible windows and finds titles, with a few aliases. | It is title-based and does not inspect a window's controls or determine automation capability. |
| Screenshot | `backend/app/agents/desktop/screen/screenshot.py` captures the primary display locally to a temporary PNG by default. | It captures the whole primary screen, not the active window; no consent/visible-sharing gate or redaction pipeline exists for model submission. |
| `inspect_screen` | `backend/app/agents/desktop/screen/inspect_screen.py` reports primary display width, height, and display count. | It does not inspect pixels, windows, controls, OCR, or screen semantics. |
| `find_ui_element` | `backend/app/agents/desktop/screen/find_ui_element.py` validates a non-empty query, then reports visual detection is not enabled. | It does not locate an element. |
| UI Automation (UIA) | `backend/app/phase4/computer/models.py` has a `ComputerElement` data shape with role, name, bounds, and interaction methods. | No UIA tree reader or semantic invoke/set-value implementation is present. The model is not proof that UIA is connected. |
| Browser | `backend/app/agents/browser/` provides URL opening and basic HTTP/HTML extraction in `tools.py`; the planner maps tasks to an operation and the executor calls the registry. | No Playwright-controlled browser session or live DOM interaction exists. HTTP parsing does not represent the live page state, authenticated browser session, or dynamic DOM. Unsupported browser actions explicitly require an adapter. |
| Planning and execution | `backend/app/agents/desktop/planner.py` creates one structured desktop action, with a text/LLM planner and fallback; `executor.py` invokes one registered tool. `backend/app/agents/desktop/verifier.py` has some action-specific checks. | There is no observe-decide-act-verify loop or generic one-action state feedback. Several low-level/controller methods return success-shaped results without observing the real application effect. |
| Verification | Desktop verification checks some application process/window state and file/folder outcomes; orchestration verification requires successful, verified steps. | Many actions trust a tool's `verified` flag rather than checking a changed control, text, title, or screen. `backend/app/orchestrator/retry_manager.py` retries failed results a fixed number of times without detecting an unchanged UI or changing control modality. |
| Safety and confirmation | `backend/app/orchestrator/coordinator.py` gates a fixed protected-action set using step/action permissions. Individual file/system/terminal tools also have confirmation checks. The low-level controller states that it does not make policy decisions. | Coverage is not a universal gate over every UI action; a generic click/type could perform a consequential operation. Extending UI control must route every action through the existing policy/confirmation path before input, without treating a learned hint as approval. |

## 2. Universal control ladder

Resolve a user goal into a sequence of **one action per step**. For each action, attempt the first applicable level below. If capability checks or verification show it is unavailable or ineffective, record the failure and advance to the next applicable level. Do not repeat an unchanged action blindly. Keyboard/menu operations in level E are a cross-cutting alternative that can be used with semantic, DOM, or vision targets; they do not bypass policy.

1. **API, CLI, or files.** Prefer deterministic interfaces when they satisfy the goal without GUI interaction. Reuse the existing CodingAgent and desktop file/terminal tools. For example, use a supported command or file operation rather than clicking through a UI. Keep existing command classification and confirmation behavior.
2. **Browser DOM through Playwright.** For web content, use an owned/explicitly selected Playwright browser context and live DOM/accessibility locators, not guessed coordinates or fetched static HTML. If the current session, authentication context, or relevant DOM cannot be safely obtained, report the limitation and continue only if another safe level can satisfy the same action.
3. **Windows UI Automation (UIA).** Inspect the target window's control tree and use stable properties (control type/role, accessible name, automation ID, enabled/focused state, and supported patterns) to invoke, select, or set a value. Avoid coordinates when a reliable semantic control exists.
4. **Vision fallback.** With explicit screenshot/LLM consent and visible indication, capture the active window by default, minimize and redact sensitive regions where feasible, and ask the existing LLM Router's vision-capable provider for a structured element description and coordinates. Render numbered set-of-marks (SoM) labels on a copy of the image and have the model refer to the numbered mark, then map it to the original bounds. The current LLM Router accepts text prompts only; multimodal request support must be added behind that existing router/provider abstraction before this level can be used. If no eligible vision provider exists, skip this level.
5. **Keyboard shortcuts and menu navigation (cross-cutting).** Prefer known standard shortcuts, discoverable UIA menu accelerators, and visible menu navigation over imprecise pointer actions. Use only a shortcut supported by observed UIA/DOM state or a high-confidence generic/app hint; otherwise ask. Keyboard input still requires focus confirmation, password-field checks, policy evaluation, and post-action verification.

### Detecting support rather than hardcoding apps

Probe capabilities for the focused window on demand and cache only a short-lived capability profile keyed by process/window identity, not a per-app execution path:

- Can the requested outcome be achieved through a known API/CLI/file operation?
- Is the target a browser page in an EVI-controlled Playwright context with an accessible live DOM?
- Can UIA attach to the window, enumerate controls, and expose useful names, roles, patterns, and bounds?
- Is a permitted vision provider configured and has the user opted in?
- Can the desired operation be expressed with a standard keyboard/menu interaction?

Measure UIA tree quality with generic signals: provider errors, tree depth/control count, proportion of unnamed controls, supported patterns, and whether likely interactive controls have usable identifiers. A poor or empty tree means UIA is unavailable for that target; continue down the ladder. Electron apps such as VS Code and games/custom-rendered canvases may expose only a window shell or incomplete tree. Do not identify these apps through app-name conditionals. Re-probe after window/process changes and keep capability results scoped and expiring.

## 3. Universal observe-decide-act-verify loop

The shared desktop control workflow should use existing `DesktopAutomationController`, agent tools, task history, orchestrator, policy gate, and Memory Service. It is not a new task system or controller. Each loop iteration handles one action, including a single UIA invoke or key press.

### Data models

- **`ScreenState`**: `window` (handle/process identity, title, bounds, foreground and integrity metadata), `elements` (bounded UIA/DOM/vision-derived `ComputerElement` records with source and confidence), optional protected/transient `screenshot_ref`, perceptual/state `hash`, observed timestamp, and available capabilities. Never persist raw screenshots by default.
- **`Action`**: action ID, goal/step ID, semantic intent, selected ladder level, target element identity or bounded coordinates, operation and arguments, expected effect, risk category, timeout, and approval reference. No credentials or raw password values.
- **`ActionResult`**: action ID, success/verified status, structured failure class, observed before/after state references, concise redacted evidence, start/end times, and whether an alternate level is eligible.
- **`Goal`**: user intent, target window/app if known, measurable success condition, risk classification, consent state for screenshots/LLM, deadline, and maximum step count.
- **`StepRecord`**: goal/action IDs, pre-state hash, chosen level, approval result, action result, post-state hash, verification evidence, retry/fallback count, and timestamp. Reuse task/step history persistence where applicable; do not create a parallel task history.

### Loop limits and stuck handling

1. Observe the target window and create `ScreenState`.
2. Decide one bounded `Action` and its expected effect.
3. Evaluate the action through the existing policy/confirmation gate; stop if denied, awaiting approval, or screenshot consent is missing.
4. Act once through the selected modality.
5. Observe again and verify the expected effect. Append a safe `StepRecord` to the current task history.
6. If state is unchanged or the effect is absent for two attempts at the same level, stop retrying that level; try another eligible ladder level or strategy only if it is still the same approved intent. After a further unsuccessful level/strategy, ask the user rather than looping.

Set an initial hard cap of 20 actions per user goal and a per-action timeout of 10 seconds (bounded configurable overrides may be justified by operation type). Overall goal deadline and every child timeout must be enforced. Emit visible progress, timeout, fallback, and stop reasons. No background retry or silent loop is permitted. Any user stop/kill-switch event cancels the current action and prevents subsequent input.

## 4. Verification and recovery

Verification must compare the expected effect with a new observation; a successful input API call alone is not proof of success.

| Expected effect | Verification evidence |
| --- | --- |
| Control opened/closed or selection changed | Re-read UIA/DOM tree and confirm the expected control/state or selected value. |
| Text entered | Read back the allowed non-sensitive field value through UIA/DOM; for inaccessible custom controls, use an opted-in redacted visual comparison. Never read back or log password content. |
| Window/app changed | Re-enumerate foreground window and compare stable window identity/title/process with the expected state. |
| Navigation or menu action | Check the new UIA/DOM structure, title/URL where available, or permitted visual state. |
| Canvas/custom-drawn action | Compare bounded before/after active-window image regions or app-provided state; require confidence threshold and user confirmation when the result is consequential. |
| Files/API/CLI action | Use the deterministic tool's return data and independently check the expected file/state where practical. |

Classify failures as `capability_unavailable`, `target_not_found`, `ambiguous_target`, `focus_lost`, `blocked_or_disabled`, `policy_denied`, `approval_required`, `password_or_sensitive_field`, `timeout`, `no_state_change`, `unexpected_state`, `provider_unavailable`, or `verification_failed`. Capability/target/focus issues can trigger a safe ladder fallback; ambiguity asks the user; policy/approval/password/stop outcomes do not fall through to a different modality to evade the restriction. Record only redacted, bounded evidence. Make retries and fallbacks visible.

## 5. Safety requirements

- Every action, including generic click, typing, UIA invoke, DOM operation, shortcut, and vision-derived input, must pass through the existing policy/confirmation gate before execution. Reuse and extend the gate, not a parallel policy engine.
- Delete, send/message, purchase/payment, submit, install, system-setting changes, credential handling, and other consequential actions always require explicit approval of the exact action and target. Neither user habits nor app hints count as approval.
- Build a global kill-switch hotkey before any UIA/vision/input automation. It must be registered outside the automation action loop, work while EVI is busy, synchronously cancel pending work, and block all future EVI mouse/keyboard input until the user explicitly re-enables control. Test keyboard-hook failure and startup state; if the kill switch is not active, control must not start.
- Never type into password/credential fields. Detect password semantics through UIA/DOM; where semantics are missing or ambiguous, do not type secrets and ask the user to enter them manually.
- Sending screenshots to an LLM is opt-in per session/goal, visibly announced, active-window-only by default, minimized/cropped to the task region where feasible, redacted where possible, transient, and deleted after use unless the user explicitly saves them. Local screenshot capture is distinct from consent to transmit.
- Show a persistent, visible **“EVI is controlling your computer”** indicator during control, with an always-available stop control as well as the global hotkey. The indicator must show when vision data is being sent.
- Screen/window inspection and app probing should collect only what is needed for the current goal. Do not capture keystrokes or retain raw screenshots by default.

## 6. Per-app hints as data

Store optional, user-owned app hints through the existing Memory Service and `memories` table. Use a namespaced key such as `app_hint:<stable-process-or-app-id>:<hint-id>` and a validated JSON value; no app-specific Python plugins or control branches.

Suggested value schema:

```json
{
  "schema_version": 1,
  "app_identity": {"process_name": "example.exe", "publisher": null},
  "kind": "shortcut | menu_path | control_quirk | verification_hint",
  "observation": "Ctrl+Shift+P opens the command palette",
  "action_scope": "open command palette",
  "source": "user_confirmed | observed",
  "confidence": 0.0,
  "created_at": "ISO-8601",
  "last_verified_at": "ISO-8601",
  "expires_at": null
}
```

Validate size, type, provenance, and timestamps; redact secrets; expire stale observations; retrieve only when process identity and action scope match. A hint proposes a strategy and never executes code, replaces fresh observation, skips verification, grants consent, or changes policy. The user must be able to view, edit, and delete hints through existing memory controls.

## 7. Phased build order and test matrix

Treat the percentages below as target verified task completion for a fixed, versioned set of safe test goals (at least 20 attempts per app type, including focus changes and expected failures). Report sample counts and confidence intervals; do not count an input API return as success. No target permits policy bypass or false-positive verification.

| App type | Test target |
| --- | ---: |
| Notepad | >= 95% |
| File Explorer | >= 90% |
| Calculator | >= 90% |
| Windows Settings | >= 85% |
| Chrome (Playwright DOM on an EVI-controlled context) | >= 95% |
| VS Code (Electron, potentially weak UIA) | >= 85% |
| Custom-drawn UI (use a neutral test app/canvas, not app-specific code) | >= 75% |

For every app type, track success by level (API/CLI, DOM, UIA, vision, keyboard), end-to-end verified completion, safe-stop correctness, median/p95 latency, and fallback count. A level that cannot apply is marked not applicable, not a failure. The end-to-end target requires that the universal ladder meets the app-type threshold; failure to meet it blocks expansion and triggers reliability work, not hardcoded per-app fixes.

### Phase 1 — Kill switch and ScreenState/UIA reading

- **Scope:** first implement and test the global kill switch; keep all control disabled until it is confirmed active. Add passive target-window observation, ScreenState, generic UIA tree reading, element bounds/patterns, stable state hash, foreground/focus metadata, and the visible control/stop indicator. No autonomous clicking or typing.
- **Likely existing files:** `backend/app/phase4/computer/controller.py`, `backend/app/phase4/computer/models.py`, `backend/app/agents/desktop/windows/utils.py`, `backend/app/agents/desktop/screen/inspect_screen.py`, and the existing desktop UI/agent entry point.
- **New files:** a generic Windows UIA adapter/state reader and tests under `backend/tests/`; no app-specific adapters.
- **Tests / acceptance:** kill switch immediately blocks an in-flight and subsequent synthetic action; controller cannot start when hook setup fails; UIA reader identifies generic names/roles/automation IDs/bounds/focus/password semantics on accessible controls; handles empty/partial trees and window changes without exceptions; app-name changes do not change logic. Test matrix records baseline UIA coverage for all seven app types.
- **Rollback:** disable passive UIA reading and restore the prior controller wiring; leave the kill-switch guard enabled anywhere input remains reachable. Never roll back by making input available without the stop mechanism.

### Phase 2 — Shared policy boundary and safe one-action loop

- **Scope:** route every desktop input route through the existing policy/confirmation gate and kill-switch check; introduce Action/ActionResult/Goal/StepRecord and one-action observe/decide/act/verify orchestration with caps and explicit progress.
- **Likely existing files:** `backend/app/orchestrator/coordinator.py`, `backend/app/orchestrator/models.py`, `backend/app/orchestrator/executor.py`, `backend/app/orchestrator/retry_manager.py`, `backend/app/agents/desktop/executor.py`, and `backend/app/phase4/computer/controller.py`.
- **Tests / acceptance:** prove all interaction modalities encounter policy first; risky categories always await approval; a stop, timeout, denied action, or invalid target ends the loop; repeated unchanged hashes switch strategy at the configured threshold and then ask the user. Confirmation behavior must remain intact.
- **Rollback:** disable the new loop and return to explicit existing agent actions while preserving the kill switch and policy boundary.

### Phase 3 — Reliable UIA actions and verification

- **Scope:** invoke controls by generic UIA patterns and verify effects by reading state; add failure classification and safe fallback decisions.
- **Likely existing files:** the Phase 1 UIA adapter, `backend/app/agents/desktop/verifier.py`, `backend/app/agents/desktop/screen/find_ui_element.py`, and `backend/app/orchestrator/verifier.py`.
- **Tests / acceptance:** fake UIA provider tests for invoke, set value, focus, disabled/ambiguous/password controls, stale elements, timeouts, and unchanged-state detection; run Notepad, Explorer, Calculator, and Settings matrix targets.
- **Rollback:** disable UIA actions but keep observation available; allow only existing explicit tools with confirmation.

### Phase 4 — Deterministic web and non-GUI paths

- **Scope:** use existing CodingAgent/file tools when GUI is unnecessary; add Playwright DOM control through a managed browser context and tie locators/actions to the common state/action/result models.
- **Likely existing files:** `backend/app/agents/browser/`, `backend/app/agents/coding/`, and shared orchestration/policy/verification modules.
- **New files:** generic Playwright adapter and focused browser tests; no separate browser task system.
- **Tests / acceptance:** validate DOM state, locator ambiguity, navigation, stale handles, consent/auth boundaries, and safety gate; Chrome DOM target >=95%. Existing HTTP browser tools continue to work as they do now.
- **Rollback:** turn off the Playwright adapter and retain existing browser behavior and UIA fallback.

### Phase 5 — Opt-in vision and set-of-marks fallback

- **Scope:** extend the existing LLM Router/provider abstraction for image input only where a vision-capable provider exists; add active-window capture, consent/indicator, minimization/redaction, numbered overlays, coordinate mapping, and visual verification.
- **Likely existing files:** `backend/app/llm/router.py`, `backend/app/llm/providers.py`, `backend/app/agents/desktop/screen/screenshot.py`, `backend/app/agents/desktop/screen/find_ui_element.py`, and controller/policy paths.
- **Tests / acceptance:** mocked vision responses verify SoM coordinate mapping; no provider call without opt-in; capture is bounded to active window/task region by default; redaction and transient deletion are tested; low-confidence matches stop safely. Run VS Code, Chrome fallback, and custom-drawn UI matrix targets.
- **Rollback:** disable image requests and vision actions; keep UIA/DOM/keyboard levels and screenshots local-only.

### Phase 6 — Keyboard/menu cross-cutting paths and per-app hints

- **Scope:** use confirmed standard shortcuts/menu navigation across targets and optionally retrieve user-owned hints from Memory Service.
- **Likely existing files:** `backend/app/memory/memory_service.py`, `backend/app/memory/schemas.py`, desktop input tools and shared verification.
- **New files:** only validated hint schema/retrieval tests and Lab memory controls if not already available; no new memory store.
- **Tests / acceptance:** stale/mismatched hints are ignored; hint deletion immediately affects retrieval; learned data cannot bypass policy; keyboard focus and password checks precede all key/text input. Complete the seven-app matrix and meet target rates before expanding actions.
- **Rollback:** disable hint retrieval and keyboard fallback independently; retain stored user data for review/deletion and keep existing memory functionality.

## 8. Risks and open questions

- **Reliability limits:** no universal interface can guarantee control of every app. Games, protected surfaces, remote sessions, custom canvases, and anti-automation software may expose no stable semantics. What should EVI do when every level is unavailable: stop, ask the user, or offer guidance only?
- **Latency and cost:** UIA/DOM probes, repeated observation, image uploads, and model fallbacks add delay and provider cost. What per-step latency and per-session vision budget is acceptable? Cache only short-lived capability data and avoid needless image calls.
- **DPI and displays:** coordinate transforms differ with per-monitor DPI, scaling, mixed resolutions, virtual desktops, and remote display changes. ScreenState must declare coordinate space and recalibrate before coordinate actions.
- **Administrative boundaries:** a non-elevated EVI process may not inspect/control elevated apps. Do not silently elevate. Should EVI always stop and ask the user to run the target at the same integrity level?
- **Focus stealing:** notifications, dialogs, and other apps can steal focus between observe and act. Revalidate foreground window immediately before input and stop if it differs from the approved target.
- **Anti-automation apps:** security-sensitive or anti-cheat applications may prohibit automation. Respect app/platform boundaries; do not evade detection or protections.
- **Privacy and retention:** what default screenshot lifetime, event retention, and app/window metadata controls should users receive? Require explicit choices before adding persistent captures or broad window monitoring.
- **Emergency behavior:** which global hotkey should be used, and how should conflicts with OS/application shortcuts be handled? The default must be configurable but fail closed if registration fails.
