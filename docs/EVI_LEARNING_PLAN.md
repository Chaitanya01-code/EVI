# EVI Day-by-Day Learning Plan

## Goal and principles

EVI should become more useful by observing opted-in work, remembering reviewed lessons, and retrieving those lessons when relevant—not by training model weights. It should start with no assumptions about a user's work and improve through evidence and feedback over time.

- The user controls what is observed, retained, used, or forgotten.
- Events and lessons must be viewable, editable, and deletable from EVI.
- Label observed facts separately from inferred lessons; retain provenance and confidence.
- Redact sensitive data before persistence or LLM use. Minimize collection and retention.
- Learning must never weaken existing policy checks. Risky actions always require the existing gate and user approval.
- Reuse the current event pipeline, PostgreSQL persistence, Memory Service, task history, and Lab; do not introduce parallel memory, task, or database systems.

## Current state to build on

- **Work events:** `backend/app/work/events/` defines `WorkEvent`, `EventCollector`, normalization, and a PostgreSQL `work_events` repository. `/work/events` can ingest and list events. `sources/nova.py` is currently empty; capture is not yet a set of active host sources.
- **Work context:** `backend/app/work/context/` builds a bounded recent-work snapshot from events, including project, application, file, branch, recent actions, and likely problems. This is current context, not durable learning.
- **Proactive signals:** `backend/app/work/proactive/` identifies a limited set of opportunities, chiefly failures. It does not yet learn user-specific habits.
- **Memory Service:** `backend/app/memory/memory_service.py` extracts durable profile facts from conversation and uses the existing `memories` table through `backend/app/database/store.py`. It supports keyed upsert, delete, and retrieval; Lab currently has a read-only memory listing.
- **Task history:** `task_history` records tasks; `task_history_steps` records orchestration steps and is exposed through the Lab executions query. A consistent record of individual tool invocations and outcomes is not yet established.
- **Policy gate:** orchestration checks protected actions in `backend/app/orchestrator/coordinator.py`; tool-specific policies also exist. `backend/phase2/decision/engine.py` provides a separate decision evaluation endpoint. Learned preferences must not bypass these controls.
- **Lab:** `backend/app/api/routes/lab/routes.py` exposes task history, executions, and memories; `frontend/src/App.jsx` and `frontend/src/services/labApi.js` are the current frontend integration points.

## Remaining features

### A. Redaction at the event normalization boundary

- **Purpose:** prevent API keys, access tokens, `.env` contents, passwords, and similar secrets from being persisted or passed to an LLM through collected events. Existing normalization redacts some command/output text, but does not comprehensively sanitize all fields and nested metadata.
- **Existing files:** `backend/app/work/events/normalizer.py`, `backend/app/work/events/collector.py`, `backend/app/work/events/models.py`, `backend/app/work/events/repository.py`; use the same sanitized event for any later LLM consumer.
- **New files:** `backend/app/work/events/redaction.py` for reusable redaction and policy tests in `backend/tests/test_work_context.py` or a focused `backend/tests/test_event_redaction.py`.
- **Data schema:** no new table. Redacted strings remain in the existing `WorkEvent` fields and `work_events` columns; preserve safe field structure while replacing secret values with a fixed marker.
- **Acceptance criteria:** tests place secret sentinels in commands, output, paths, and nested metadata and confirm none survive normalization, database arguments, or LLM-bound event payloads; benign text remains intact; `.env` file contents are never collected as event payloads.

### B. Opt-in work event sources

- **Purpose:** observe enough work context to learn useful patterns, without recording file contents or continuously collecting more than needed.
- **Existing files:** `backend/app/work/events/base.py`, `backend/app/work/events/collector.py`, `backend/app/work/events/sources/nova.py`, `backend/app/work/events/models.py`, `backend/app/work/events/repository.py`, and `backend/app/work/context/`.
- **New files:** `backend/app/work/events/sources/file_changes.py`, `git.py`, and `active_window.py`; add focused source tests under `backend/tests/`.
- **Data schema:** reuse `WorkEvent` and `work_events`. File events carry event type, normalized project/workspace and path, timestamp, and source; Git events carry project, branch and event type; sampled window events carry application name and title only. Do not store file contents, keystrokes, screenshots, or window contents.
- **Acceptance criteria:** each source can be individually enabled/disabled and emits normalized, redacted events; file watching ignores configured paths and avoids duplicate/noisy events; Git capture is scoped to selected repositories; active-window capture is sampled at a configurable, non-excessive interval and can be disabled; source failures are visible and do not silently create success-shaped events.

### C. User feedback records

- **Purpose:** capture whether a proposal or inferred lesson matched the user's intent, including corrections that provide stronger evidence than passive observation.
- **Existing files:** `backend/app/database/store.py`, `backend/app/database/connection.py`, `backend/app/database/lab_store.py`, and task/feedback integration in `backend/app/router/intent_router.py`.
- **New files:** `backend/app/database/feedback.py` (record model and persistence helpers), plus focused persistence and API tests.
- **Data schema:** add a `learning_feedback` table in the existing PostgreSQL database: `id`, `user_id`, optional `task_id`/`event_id`, `proposal`, `response` constrained to `accepted|rejected|corrected`, nullable `correction_text`, `task_type`, and `timestamp` (plus normal created/updated timestamps if needed). Index by user, task type, and timestamp. Redact free text before storage.
- **Acceptance criteria:** accepted, rejected, and corrected responses persist with task type and time; corrections are retained as user-authored evidence; invalid response values fail validation; records can be retrieved and deleted by the user; database errors are surfaced.

### D. Persist individual tool executions

- **Purpose:** make the Lab execution history reflect real tool activity and allow outcome rates to be calculated, rather than inferring tool activity from task-level results.
- **Existing files:** `backend/app/database/orchestration_history.py`, `backend/app/database/store.py`, `backend/app/database/lab_store.py`, `backend/app/api/routes/lab/routes.py`, and each shared agent/tool execution path as appropriate.
- **New files:** `backend/app/database/tool_execution.py` for the record model; a focused test module.
- **Data schema:** add `tool_executions` to the existing PostgreSQL database: `id`, `task_id`, optional `step_id`, `session_id`, `user_id`, `task_type`, `agent_type`, `tool_name`, redacted input summary, redacted output summary, `status`, `success`, `verified`, `error` (redacted), `started_at`, `completed_at`, and `timestamp`. Index by task, user, task type, and time. Keep detailed credentials and unbounded raw output out of records.
- **Acceptance criteria:** each executed tool produces one durable outcome record, including failures; Lab `/executions` returns paginated records from this store; success counts reconcile with persisted executions over a fixed test fixture; existing task and orchestration histories remain unchanged.

### E. Nightly lesson consolidation

- **Purpose:** turn a day's redacted work events, outcomes, and user feedback into concise, reviewable lessons, rather than retaining noisy activity as supposed knowledge.
- **Existing files:** `backend/app/work/events/repository.py`, `backend/app/database/feedback.py` (after C), `backend/app/memory/memory_service.py`, `backend/app/database/store.py`, and `backend/app/database/connection.py`.
- **New files:** `backend/app/memory/consolidation.py` and a bounded scheduled-job entry point such as `backend/app/memory/nightly_job.py`; use the repository's deployment/scheduling mechanism rather than adding a second worker framework.
- **Data schema:** extend existing `memories` rows with lesson provenance such as `source_event_ids` (JSONB), `source_feedback_ids` (JSONB), `source_date` (DATE), and `updated_at`; retain `key`, `value`, `memory_type`, and `confidence`. A lesson has an owner, stable key, concise text, type, confidence, date, and source references. Store lessons using Memory Service/database helpers, not a new memory store.
- **Acceptance criteria:** a deterministic test day's events and feedback produce short lessons with source IDs, date, and confidence; rejected/corrected feedback is honored; duplicate lessons update rather than multiply; no lesson is written before redaction and it remains editable/deletable through the same memory API; job is idempotent for a date and reports failures.

### F. Layered memory using existing storage

- **Purpose:** distinguish observed history from reusable knowledge and repeatable procedures without creating a second memory system.
- **Existing files:** `backend/app/memory/schemas.py`, `backend/app/memory/memory_service.py`, `backend/app/database/store.py`, `backend/app/database/models.py`, and `backend/app/work/events/repository.py`.
- **New files:** none required; add schema/service tests. Add a migration only if the existing `memories` table needs the provenance columns in E.
- **Data schema:** episodic memory is the existing `work_events` log with retention controls; semantic and procedural memories are rows in existing `memories`, using `memory_type='semantic'` for project/style facts and `memory_type='procedural'` for validated workflows. Profile facts continue to use the existing type. Confidence and provenance are retained per learned lesson.
- **Acceptance criteria:** retrieval can filter by layer and user/project scope; no duplicate event or separate task-history table is introduced; low-confidence or contradicted lessons can be reviewed and corrected; retention/deletion behavior covers both source events and derived lessons.

### G. Retrieve lessons for planning

- **Purpose:** supply only relevant, trusted lessons to the planner so EVI can adapt to the current project and task without flooding prompts or treating guesses as facts.
- **Existing files:** `backend/app/memory/memory_service.py`, `backend/app/router/intent_router.py`, `backend/app/agents/desktop/planner.py`, other agent planner entry points under `backend/app/agents/`, and `backend/app/orchestrator/planner.py`.
- **New files:** `backend/app/memory/retrieval.py` for bounded relevance ranking and filtering; focused retrieval/prompt tests.
- **Data schema:** no new table. Read lesson rows from existing `memories`, filtering by user, layer, project/task type, confidence, and recency where applicable; preserve source/date metadata in the retrieved result.
- **Acceptance criteria:** matching lessons appear in the planner context with provenance; unrelated lessons do not; prompt size is bounded; absent or low-confidence memory leaves current behavior unchanged; retrieval does not call an LLM or authorize tools.

### H. Acceptance rates and a gated autonomy ladder

- **Purpose:** let EVI ask less often for low-risk, well-understood tasks when a sustained history supports it, while preserving user control and all existing risky-action confirmations.
- **Existing files:** `backend/app/database/feedback.py`, `backend/app/database/lab_store.py`, `backend/app/orchestrator/coordinator.py`, `backend/phase2/decision/engine.py`, `backend/app/task/task_manager.py`, and Lab routes.
- **New files:** `backend/app/memory/autonomy.py` for rate calculation and a policy decision model; focused policy and metric tests.
- **Data schema:** derive per-user/per-task-type acceptance counts and rates from `learning_feedback` over a documented time window; optionally persist a user-selected autonomy level in the existing `memories` table. Do not create a separate task or policy database.
- **Acceptance criteria:** Lab shows numerator, denominator, window, and rate per task type; insufficient samples or stale/low rates stay at “ask every time”; sustained acceptance may advance only through “ask briefly” to “act and report”; each transition is explainable and reversible; protected/risky actions always require the existing policy gate and explicit approval regardless of score.

### I. Lab learning review

- **Purpose:** make collected evidence, feedback, and learned lessons transparent and controllable by the user.
- **Existing files:** `backend/app/api/routes/lab/routes.py`, `backend/app/api/lab_schemas.py`, `backend/app/database/lab_store.py`, `backend/app/memory/memory_service.py`, `frontend/src/App.jsx`, `frontend/src/services/labApi.js`, and existing Lab components/styles.
- **New files:** a focused learning/memory Lab page or component under `frontend/src/pages/lab/` or `frontend/src/components/lab/`; API request/response schemas and tests as needed.
- **Data schema:** APIs expose existing `work_events`, `learning_feedback`, and `memories`/lesson rows with provenance and confidence; add no frontend-owned persistence.
- **Acceptance criteria:** user can page/search events and lessons, inspect sources/confidence/date, edit a lesson, delete a lesson or selected event, and review/submit feedback; mutations persist and are reflected on refresh; confirmation precedes destructive bulk deletion; sensitive values remain redacted in API responses.

### J. Later capabilities

- **Purpose:** add richer evidence only after consent, redaction, event control, and review workflows are dependable.
- **Existing files:** `backend/app/agents/desktop/screen/inspect_screen.py`, `backend/app/agents/browser/`, the existing event and memory modules, and their policy/confirmation paths.
- **New files:** a browser DOM/accessibility adapter next to `backend/app/agents/browser/`; optional screen-event adapter in `backend/app/work/events/sources/`; any optional local fine-tuned model integration must be isolated behind an explicit opt-in, separate evaluation, and rollback.
- **Data schema:** screen understanding should store only user-approved, minimal structured observations in existing event/memory schemas; browser DOM is transient by default. Fine-tuning data/weights are not part of memory and must not be generated from private work without explicit consent.
- **Acceptance criteria:** screen/browser capture is opt-in, visibly active, redacted, bounded, and deletable; DOM actions still pass the existing policy gate; a local fine-tuned brain is optional and never required for memory learning or safe operation.

## Build order, tests, and rollback

1. **Safety boundary:** implement A and its tests first. Test nested metadata, secret formats, and redaction before database/LLM boundaries. Rollback: disable the new source/LLM consumers; retain the old event schema, but do not roll back redaction for newly captured data.
2. **Controlled observation:** add B behind opt-in settings and test each source, disabled mode, filtering, sampling, and duplicate suppression. Rollback: disable each source; keep already collected events subject to user deletion/retention controls.
3. **Measure real outcomes:** add C and D with PostgreSQL migration tests, failure cases, and Lab pagination tests. Rollback: disable writes/endpoints and remove only new tables after export/backup and explicit data-retention approval; preserve existing task history.
4. **Learn transparently:** implement E and F with deterministic fixtures, idempotency, provenance, confidence, corrections, and CRUD tests. Rollback: stop the scheduled job and disable lesson retrieval; preserve user-authored and previously reviewed memories unless the user chooses deletion.
5. **Use lessons safely:** implement G, then H. Test prompt relevance/size and policy invariants, especially protected actions at every autonomy level. Rollback: turn off retrieval/autonomy and return to “ask every time”; never disable the policy gate.
6. **Expose controls:** implement I and end-to-end API/UI tests for view, edit, delete, and redaction. Rollback: hide the new Lab entry point while keeping existing Lab routes and stored data intact.
7. **Optional sensors/models:** consider J only after privacy review and separate opt-in tests. Rollback: disable the adapter/model and delete its derived records on request.
8. **Housekeeping:** rename `ARCHITEXTURE.md` to `ARCHITECTURE.md`, then move `backend/phase2/` to `backend/app/phase2/` and update imports such as `from phase2...` across backend and tests. Run the full backend test suite and import checks. Rollback: revert only the rename/move and corresponding import changes; do not combine this migration with a learning-data migration.

## Risks and open questions

- **Privacy:** Which folders, repositories, apps, and window titles may be observed? What are default retention periods, local-only options, and consent controls? Window titles and paths can themselves contain sensitive information.
- **Wrong lessons:** How should confidence thresholds, contradiction handling, and lesson expiry work? Require provenance, user correction, and a simple “forget this” control; do not promote a single observation into a durable rule.
- **Performance:** What event rates, file-watch debounce, active-window sample interval, consolidation time budget, and retrieval latency are acceptable? Bound every query, prompt contribution, and job batch.
- **Autonomy:** What sample minimum, sustained acceptance threshold, and evaluation window qualify as “high”? Choose and expose these before enabling advancement; never let a global rate hide poor outcomes for a specific task type.
- **Operations:** Where will the nightly job run, how will retries and duplicate runs be handled, and what backup/export path is required before schema or retention changes?
- **Access control:** Current Lab access is not a substitute for user authentication. Restrict private learning data to its owner before exposing it beyond a single-user local setup.
