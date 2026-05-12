# Aardvark — Full Frontend ↔ Backend Correlation Audit

## 1. System Correlation Map

| Feature | Frontend Component | Backend Endpoint | Orchestrator/Service | Status |
|---------|-------------------|------------------|----------------------|--------|
| **Workspace Creation** | `JobWorkspacePanel.jsx` | `POST /api/v1/scrape` | `execution_manager.py` | PARTIAL |
| **Execution Preview** | *Missing UI* | `GET /api/v1/scrape/preview` | `ExecutionContext.get_plan_preview` | MISSING |
| **Source Selection** | `AdvancedOptionsPanel.jsx` | `POST /api/v1/scrape` | `schemas/scrape.py` validator | BROKEN (Payload drift) |
| **Execution Run** | `RunTaskBar.jsx` | `POST /api/v1/scrape` | `scrape_contract.py` | CONNECTED |
| **Status Polling** | `RunProgressCard.jsx` | `GET /api/v1/scrape/{id}/status` | `async_recovery.py` | PARTIAL |
| **Export/Results** | `ResultsWorkbench.jsx` | `GET /api/v1/scrape/{id}/export` | `scrape_contract.py` filter | CONNECTED |

## 2. Missing Features Report

* **Missing UI Integrations:** `Execution Plan Preview` is generated deterministically by the backend before locking, but the frontend lacks a confirmation modal to consume it.
* **Orphan Backend Logic:** `rank_and_classify_page()` (Relevance Ranking) operates on the backend, but the frontend lacks an analytics panel to show why pages were skipped. 
* **Partial Implementations:** `AsyncRecoveryManager` writes checkpoint persistence locally. The frontend polling (`RunProgressCard.jsx`) does not yet incrementally stream these checkpoints, leading to a disconnected UI state during long runs.

## 3. Duplication & Architectural Drift Report

* **Duplicate Normalization:** Phone number format validation exists historically in both `frontend/src/utils/helpers.js` and backend `security_guard.py`, conflicting with the new deterministic `_normalize_phone_number` in `scrape_contract.py`.
  * *Recommended Source:* `backend/app/services/scrape_contract.py`
* **Architectural Drift:** `backend/app/orchestrator/dashboard_orchestrator.py.bak` and `history_orchestrator.py.bak` are dead architectural remnants that bypass the schema purity engine.
* **Stale Execution Paths:** The frontend payload builder dynamically injects `["internal", "google_maps"]` which violently conflicts with the new strict compatibility matrix.

## 4. Execution Consistency Report

* **Status Inconsistencies:** 
  * The frontend optimistically assumes `COMPLETED` when the HTTP request returns. 
  * *Fix Required:* UI must parse the unified `CANONICAL_STATUS_VALUES` (e.g., `PARTIAL_SUCCESS`, `TIMEOUT_RECOVERED`) directly from the backend payload.
* **Contract Inconsistencies:** The frontend is not universally passing `workspace_type` or `strict_extraction: true`, relying on backend fallbacks.

## 5. Reliability Risks

* **Persistence Risk (High):** Local `/tmp` filesystem checkpoints block horizontal Kubernetes/Docker scaling.
* **Timeout Risk (Medium):** The frontend relies on standard HTTP polling. Long running executions could flap if the polling interval triggers rate limits before the backend writes the next checkpoint.

## 6. Refactor Priorities

* **P0 → Critical:** Update `JobWorkspacePanel.jsx` to stop injecting forced multi-source arrays; rely strictly on `["web"]`.
* **P0 → Critical:** Force frontend state hooks to sync explicitly with backend `CANONICAL_STATUS_VALUES`.
* **P1 → High:** Migrate `AsyncRecoveryManager` persistence to Redis/Postgres.
* **P2 → Medium:** Build the Execution Preview UI confirmation modal.
* **P3 → Cleanup:** Delete all `.bak` orchestrator files and duplicated normalization hooks.

## 7. Production Readiness Score
**65 / 100**
(Backend is hardened, but Frontend payload drift and isolated checkpoints drag the score down.)

## 8. Final Verdict
**ARCHITECTURALLY UNSTABLE (Frontend-to-Backend Mismatch)**
The backend orchestration is a deterministic execution truth system, but the frontend operates as a legacy optimistic best-effort UI. The system cannot be considered production-ready until the frontend is fully stripped of orchestration authority and bound explicitly to the backend contracts.
