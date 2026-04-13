# Smart Scraper Platform - API & Frontend Integration Audit

**Date:** April 13, 2026  
**Status:** Comprehensive Audit Complete

---

## 1. BACKEND API INVENTORY

### Root Routes
- `GET /health` - Basic health check (status, service, version, environment, services)
- `GET /health/full` - Detailed health check (database, redis, playwright, openai)

### Authentication Endpoints (`/api/v1/auth`)
| Method | Path | Parameters | Returns | Auth Required |
|--------|------|-----------|---------|---------------|
| POST | `/auth/register` | email, password | UserResponse (201) | No |
| POST | `/auth/login` | username (email), password | TokenResponse | No |
| GET | `/auth/me` | - | UserResponse | Yes |

**Authentication Flow:** OAuth2 password flow with JWT tokens. Tokens stored in localStorage on frontend.

### Account Management (`/api/v1/account`)
| Method | Path | Parameters | Returns | Auth Required |
|--------|------|-----------|---------|---------------|
| GET | `/account/usage` | - | UsageResponse | Yes |
| GET | `/account/plan` | - | PlanLimitsResponse | Yes |
| GET | `/account/summary` | - | AccountSummaryResponse | Yes |

**Data Returned:**
- Plan information (name, limits)
- Usage metrics (jobs, runs, storage)
- Limits enforcement

### User Data Management (`/api/v1/user`)
| Method | Path | Parameters | Returns | Auth Required |
|--------|------|-----------|---------|---------------|
| GET | `/user/storage-summary` | - | StorageCleanupEstimateResponse | Yes |
| DELETE | `/user/history` | - | CleanupResultResponse | Yes |
| DELETE | `/user/temp-files` | - | CleanupResultResponse | Yes |
| DELETE | `/user/clear-all` | - | CleanupResultResponse | Yes |
| GET | `/user/activity` | limit, offset | Dict[str, Any] | Yes |
| GET | `/user/history` | start_date, end_date, item_type | Dict[str, Any] | Yes |
| DELETE | `/user/history/{item_id}` | item_type (job\|run\|export) | Dict[str, bool] | Yes |

### Jobs Management (`/api/v1/jobs`)
| Method | Path | Parameters | Returns | Auth Required |
|--------|------|-----------|---------|---------------|
| POST | `/jobs` | JobCreate | JobResponse (201) | Yes |
| GET | `/jobs` | skip, limit | JobListResponse | Yes |
| GET | `/jobs/{job_id}` | - | JobResponse | Yes |
| POST | `/jobs/{job_id}/runs` | - | RunResponse (201) | Yes |
| GET | `/jobs/{job_id}/runs` | skip, limit | RunListResponse | Yes |
| DELETE | `/jobs/{job_id}` | - | 204 No Content | Yes |

**Job Creation Parameters:**
- url (required)
- login_url (optional)
- login_username (optional)
- login_password (optional)
- scrape_type (required)
- prompt (optional)
- max_pages (default: 10)
- follow_pagination (default: true)

### Runs Management (`/api/v1/runs`)
| Method | Path | Parameters | Returns | Auth Required |
|--------|------|-----------|---------|---------------|
| GET | `/runs` | skip, limit | RunListResponse | Yes |
| GET | `/runs/{run_id}` | - | RunResponse | Yes |
| GET | `/runs/{run_id}/logs` | - | Dict with logs array | Yes |
| POST | `/runs/{run_id}/retry` | - | RunResponse (201) | Yes |
| GET | `/runs/{run_id}/markdown` | - | Dict with markdown snapshot | Yes |
| GET | `/runs/{run_id}/results` | skip, limit | ResultListResponse | Yes |

### Results Management (`/api/v1/results`)
| Method | Path | Parameters | Returns | Auth Required |
|--------|------|-----------|---------|---------------|
| GET | `/results/{result_id}` | - | ResultResponse | Yes |

### Exports Management (`/api/v1/exports`)
| Method | Path | Parameters | Returns | Auth Required |
|--------|------|-----------|---------|---------------|
| POST | `/exports` | run_id, format | ExportResponse (201) | Yes |
| GET | `/exports` | skip, limit | ExportListResponse | Yes |
| GET | `/exports/{export_id}` | - | ExportResponse | Yes |
| GET | `/exports/{export_id}/download` | - | FileResponse (blob) | Yes |
| POST | `/exports/download` | Array<UUID> (export_ids) | FileResponse (ZIP) | Yes |

**Export Formats:** excel, pdf, word, json

### API Keys Management (`/api/v1/api-keys`)
| Method | Path | Parameters | Returns | Auth Required |
|--------|------|-----------|---------|---------------|
| POST | `/api-keys` | name | ApiKeyCreateResponse (201) | Yes |
| GET | `/api-keys` | skip, limit | ApiKeyListResponse | Yes |
| DELETE | `/api-keys/{api_key_id}` | - | 204 No Content | Yes |

**Response:** Full key only returned once on creation; preview format "sk_live_****..." stored afterwards

### Credentials Management (`/api/v1/credentials`)
| Method | Path | Parameters | Returns | Auth Required |
|--------|------|-----------|---------|---------------|
| POST | `/credentials` | provider, api_key | CredentialResponse (201) | Yes |
| GET | `/credentials` | skip, limit | CredentialListResponse | Yes |
| DELETE | `/credentials/{provider}` | - | 204 No Content | Yes |

**Providers:** openai, serper, gemini

### Scraping Types (`/api/v1/scraping-types`)
| Method | Path | Parameters | Returns | Auth Required |
|--------|------|-----------|---------|---------------|
| GET | `/scraping-types` | - | List[ScrapingTypeInfo] | No |

### System Diagnostics (`/api/v1/system`)
| Method | Path | Parameters | Returns | Auth Required |
|--------|------|-----------|---------|---------------|
| GET | `/system/diagnostics` | - | Dict with diagnostics | No |

### Demo (`/api/v1/demo`)
| Method | Path | Parameters | Returns | Auth Required |
|--------|------|-----------|---------|---------------|
| GET | `/demo/overview` | - | Dict with demo data | No |

---

## 2. FRONTEND INTEGRATION POINTS

### Page Components and API Usage

#### DashboardPage.jsx ([DashboardPage.jsx](frontend/src/pages/DashboardPage.jsx#L83-L85))
- **Load Dashboard Data:** 
  - `api.getJobs()` → GET `/jobs`
  - `api.getRuns()` → GET `/runs`
  - `api.getAccountSummary()` → GET `/account/summary`
  - `api.getResults(runId)` → GET `/runs/{run_id}/results`
- **Recent Requests:** From localStorage via assistant orchestrator
- **Polling:** Polls active runs every 4 seconds (ACTIVE_RUN_POLL_INTERVAL_MS)

#### NewJobPage.jsx ([NewJobPage.jsx](frontend/src/pages/NewJobPage.jsx#L193-L203))
- **Create Job:** `api.createJob()` → POST `/jobs`
- **Start Run:** `api.startJobRun(jobId)` → POST `/jobs/{job_id}/runs`
- **Data Types:** Uses DataTypeSelector component for scrape_type
- **Login Fields:** Supports login_url, login_username, login_password

#### JobDetailPage.jsx ([JobDetailPage.jsx](frontend/src/pages/JobDetailPage.jsx#L214-L283))
- **Load Job Data:** 
  - `api.getJob(id)` → GET `/jobs/{job_id}`
  - `api.getRunsByJob(id)` → GET `/jobs/{job_id}/runs`
- **Load Run Details:**
  - `api.getResults(runId)` → GET `/runs/{run_id}/results`
  - `api.getRunLogs(runId)` → GET `/runs/{run_id}/logs`
- **Run Actions:**
  - `api.startJobRun(id)` → POST `/jobs/{job_id}/runs`
  - `api.retryRun(runId)` → POST `/runs/{run_id}/retry`
- **Export Creation:** `api.createExport({run_id, format})` → POST `/exports`
- **Polling:** Continuously updates run details every 4 seconds

#### ExportsPage.jsx ([ExportsPage.jsx](frontend/src/pages/ExportsPage.jsx#L1-L40))
- **List Exports:** `api.getExports()` → GET `/exports`
- **Download Export:** `api.downloadExport(exportId)` → GET `/exports/{export_id}/download`

#### ApiKeysPage.jsx ([ApiKeysPage.jsx](frontend/src/pages/ApiKeysPage.jsx#L24-L51))
- **List Keys:** `api.getApiKeys()` → GET `/api-keys`
- **Create Key:** `api.createApiKey({name})` → POST `/api-keys`
- **Delete Key:** `api.deleteApiKey(keyId)` → DELETE `/api-keys/{api_key_id}`

#### AiIntegrationsPage.jsx ([AiIntegrationsPage.jsx](frontend/src/pages/AiIntegrationsPage.jsx#L1-L30))
- **List Credentials:** `api.getCredentials()` → GET `/credentials`
- **Save Credential:** `api.saveCredential({provider, api_key})` → POST `/credentials`
- **Delete Credential:** `api.deleteCredential(provider)` → DELETE `/credentials/{provider}`

#### AccountPage.jsx ([AccountPage.jsx](frontend/src/pages/AccountPage.jsx#L23))
- **Load Summary:** `api.getAccountSummary()` → GET `/account/summary`
- **List Jobs/Runs/Exports:** Fetches all three resources together
- **Display Limits:** Shows plan info, jobs remaining, runs remaining

#### SettingsPage.jsx ([SettingsPage.jsx](frontend/src/pages/SettingsPage.jsx#L21-L61))
- **Get Storage Summary:** `api.getStorageCleanupSummary()` → GET `/user/storage-summary`
- **Clear History:** `api.clearHistory()` → DELETE `/user/history`
- **Clear Temp Files:** `api.clearTempFiles()` → DELETE `/user/temp-files`
- **Clear All Data:** `api.clearAllUserData()` → DELETE `/user/clear-all`

#### HistoryPage.jsx ([HistoryPage.jsx](frontend/src/pages/HistoryPage.jsx))
- **Component:** HistoryTable component
- **APIs Used:** `api.getUserHistory()`, `api.deleteHistoryItem()`

#### LoginPage.jsx ([LoginPage.jsx](frontend/src/pages/LoginPage.jsx))
- **Login:** `api.login(email, password)` → POST `/auth/login`
- **Register:** `api.register(userData)` → POST `/auth/register`
- **Get User:** `api.getCurrentUser()` → GET `/auth/me`

### Component-Level API Usage

#### ActivityTimeline.jsx
- `api.getUserActivity({limit: 20})` → GET `/user/activity`

#### DiagnosticsWidget.jsx
- `api.getSystemDiagnostics()` → GET `/system/diagnostics`

#### StakeholderDemoPanel.jsx
- `api.getDemoOverview()` → GET `/demo/overview`

#### ExportManagementPanel.jsx
- `api.getExports({limit: 50})` → GET `/exports`
- `api.downloadExport(exportId)` → GET `/exports/{export_id}/download`
- `api.downloadMultipleExports(selectedExports)` → POST `/exports/download`

#### JobWorkspacePanel.jsx
- `api.getJob(jobId)` → GET `/jobs/{job_id}`
- `api.getRunsByJob(jobId)` → GET `/jobs/{job_id}/runs`
- `api.getResults(runId)` → GET `/runs/{run_id}/results`
- `api.getRunLogs(runId)` → GET `/runs/{run_id}/logs`
- `api.startJobRun(jobId)` → POST `/jobs/{job_id}/runs`
- `api.retryRun(runId)` → POST `/runs/{run_id}/retry`
- `api.createExport({run_id, format})` → POST `/exports`

#### RecentRunsCard.jsx
- `api.getRunMarkdown(runId)` → GET `/runs/{run_id}/markdown`

---

## 3. IDENTIFIED GAPS & MISMATCHES

### Gap #1: Missing Frontend Implementation for Delete Job
**Severity:** MEDIUM  
**Backend Endpoint:** `DELETE /jobs/{job_id}` ([jobs.py](backend/app/api/v1/jobs.py#L376))  
**Frontend Usage:** ❌ NOT IMPLEMENTED  
**Issue:** Backend supports job deletion but no UI component calls this API  
**Impact:** Users cannot delete jobs through the UI  
**Fix Needed:** Add delete button to JobDetailPage or job list with confirmation dialog

### Gap #2: Incomplete ZIP Download for Multiple Exports
**Severity:** HIGH  
**Backend Endpoint:** `POST /exports/download` ([exports.py](backend/app/api/v1/exports.py#L283-L336))  
**Implementation Status:** ⚠️ PARTIAL  
**Code Location:** [exports.py Line 335-336](backend/app/api/v1/exports.py#L335-L336)  
```python
# TODO: Create ZIP file with multiple exports
# For now, return the first export (implement ZIP later if needed)
```
**Frontend Usage:** ✅ IMPLEMENTED - `api.downloadMultipleExports()` called from ExportManagementPanel.jsx  
**Issue:** Backend returns only first export, not actual ZIP file  
**Fix Needed:** Implement proper ZIP file creation with all selected exports

### Gap #3: User History API Redundancy
**Severity:** LOW  
**Backend Issue:** Duplicate route decorators in [user.py](backend/app/api/v1/user.py)  
**Location:** Lines 103, 113, 133 have duplicate @router decorators  
**Impact:** Potential route conflicts or undefined behavior  
**Fix Needed:** Remove duplicate decorators

### Gap #4: Missing Error Cases in History Endpoints
**Severity:** MEDIUM  
**Frontend:** `api.getUserHistory()` and `api.deleteHistoryItem()` are called  
**Backend:** Routes exist but error handling for invalid item_type parameter not validated  
**Issue:** Frontend passes item_type but backend doesn't validate against allowed values (job, run, export)  
**Fix Needed:** Add enum validation for item_type parameter

### Gap #5: API Key Missing in Exports Create
**Severity:** MEDIUM  
**Endpoint:** `POST /exports` ([exports.py](backend/app/api/v1/exports.py#L39-L105))  
**Authentication:** Requires `verify_api_key` dependency  
**Frontend Implementation:** ❌ NOT IMPLEMENTED  
**API Call Location:** [JobDetailPage.jsx](frontend/src/pages/JobDetailPage.jsx) and components  
**Issue:** API has optional/required API key verification but frontend doesn't handle it  
**Impact:** Export creation might fail silently if API key requirement is enforced  
**Fix Needed:** Check if this requirement is intentional; if so, document or add to frontend

---

## 4. MISSING IMPLEMENTATIONS

### Feature: Job Deletion UI
**Requirement:** Users cannot delete jobs  
**Backend Status:** ✅ IMPLEMENTED - `DELETE /jobs/{job_id}`  
**Frontend Status:** ❌ MISSING  
**Priority:** MEDIUM  
**Files Affected:** JobDetailPage.jsx, HistoryTable.jsx  
**Implementation Needed:**
- Add delete button with confirmation
- Call `api.deleteJob(jobId)` (needs to be added to api.js)
- Handle success/error states

### Feature: Update/Edit Jobs
**Backend Status:** ❌ NOT IMPLEMENTED - No PUT/PATCH endpoint  
**Frontend Status:** ❌ NOT IMPLEMENTED  
**Current Flow:** Create new job if changes needed  
**Priority:** MEDIUM  
**Missing Endpoints:**
- `PATCH /jobs/{job_id}` - Partial update (url, prompt, max_pages, etc.)
- `PUT /jobs/{job_id}` - Full job update

### Feature: Job Cancellation
**Backend Status:** ❌ NOT IMPLEMENTED  
**Frontend Status:** ❌ NOT IMPLEMENTED  
**Use Case:** Cancel pending/running jobs mid-execution  
**Missing Endpoint:** `POST /jobs/{job_id}/cancel` or `POST /runs/{run_id}/cancel`  
**Priority:** HIGH

### Feature: Run Deletion
**Backend Status:** ❌ NOT IMPLEMENTED  
**Frontend Status:** ❌ NOT IMPLEMENTED  
**Use Case:** Users cannot delete individual runs  
**Missing Endpoint:** `DELETE /runs/{run_id}`  
**Priority:** MEDIUM

### Feature: Export Deletion  
**Backend Status:** ❌ NOT IMPLEMENTED  
**Frontend Status:** ❌ NOT IMPLEMENTED  
**Use Case:** Users cannot delete exports to free storage  
**Missing Endpoint:** `DELETE /exports/{export_id}`  
**Priority:** HIGH

### Feature: Bulk Export Format Conversion
**Backend Status:** ❌ NOT IMPLEMENTED  
**Frontend Status:** ❌ NOT IMPLEMENTED  
**Use Case:** Export runs in multiple formats simultaneously  
**Missing Endpoint:** `POST /runs/{run_id}/exports/batch` with format array  
**Priority:** LOW

### Feature: Authentication: Logout Endpoint
**Backend Status:** ❌ NOT IMPLEMENTED  
**Frontend Status:** ✅ PARTIAL - `localStorage.clear()` used  
**Current Implementation:** Frontend clears tokens on 401 or manual logout redirect  
**Missing Endpoint:** `POST /auth/logout` - Optional server-side token blacklist  
**Priority:** LOW

### Feature: Export Regeneration
**Backend Status:** ❌ NOT IMPLEMENTED  
**Frontend Status:** ❌ NOT IMPLEMENTED  
**Use Case:** Regenerate export if file corrupted  
**Missing Endpoint:** `POST /exports/{export_id}/regenerate`  
**Priority:** LOW

---

## 5. INTEGRATION ISSUES

### Issue #1: Authentication Flow (Clerk Integration Mismatch)
**File References:**
- Backend: [auth.py](backend/app/api/v1/auth.py) - Email/password OAuth2 flow
- Frontend: [LoginPage.jsx](frontend/src/pages/LoginPage.jsx), [AuthContext.jsx](frontend/src/context/AuthContext.jsx)

**Problem:** 
- Backend implements traditional email/password auth  
- Frontend may expect Clerk integration (referenced in PR descriptions)  
- Current implementation is basic JWT token storage in localStorage

**Impact:** 
- No persistent session management  
- No refresh tokens implemented  
- No server-side token revocation  
- User still logged in client-side even if server session expires

**Remediation:**
1. Clarify auth strategy (Clerk vs. JWT)
2. Implement refresh token rotation if using JWT
3. Add server-side logout endpoint
4. Implement token blacklist or expiry enforcement

### Issue #2: Rate Limiting Middleware Present but Not Tested
**Location:** [main.py Line 77](backend/app/main.py#L77), [rate_limit.py](backend/app/middleware/rate_limit.py)

**Headers Added:** X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Window

**Frontend Status:** Rate limiting headers not consumed/displayed to user

**Remediation:** Implement frontend rate limit handling with user notifications

### Issue #3: CORS Configuration
**Location:** [main.py Lines 74-79](backend/app/main.py#L74-L79)

**Current Settings:**
```python
allow_credentials=True
allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
allow_headers=["Authorization", "Content-Type", settings.API_KEY_HEADER_NAME]
```

**Frontend Impact:** 
- API calls should include credentials  
- Api.js passes Authorization header correctly  
- API key header also allowed (settings.API_KEY_HEADER_NAME)

**Verification Needed:** Test cross-origin credentials with actual deployment hosts

### Issue #4: Request Size & Timeout Limits
**Location:** [main.py Lines 102-103](backend/app/main.py#L102-L103)

**Limits:**
- MAX_REQUEST_SIZE_BYTES: Check in config  
- REQUEST_TIMEOUT_SECONDS: Check in config  
- API client timeout: 30,000ms (30 seconds) [api.js Line 112](frontend/src/services/api.js#L112)

**Risk:** 
- Large file uploads might fail with 413 Payload Too Large  
- Long-running exports might timeout at 30 seconds

**Remediation:** 
- Increase frontend timeout for export operations  
- Stream large file uploads  
- Implement progress-based polling for async operations

### Issue #5: API Base URL Configuration
**Location:** [api.js Lines 3-15](frontend/src/services/api.js#L3-L15)

**Current Logic:**
```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 
  (isLocalDevHost ? 'http://127.0.0.1:8000/api/v1' : '/api/v1')
```

**Environment Handling:**
- Development: Direct to localhost:8000
- Production: Uses relative path `/api/v1` (requires proxy)

**Issues:**
- Production deployment needs proper reverse proxy configuration  
- No fallback if proxy misconfigured  
- Environment variable must be set explicitly

**Remediation:**
- Document API_URL configuration for deployment  
- Add fallback logic  
- Validate API availability on frontend start

### Issue #6: Error Message Extraction Too Aggressive
**Location:** [api.js Lines 57-90](frontend/src/services/api.js#L57-L90)

**Problem:** Complex error parsing logic might hide actual issues or show confusing messages

**Frontend Handling:**
- 422 Validation errors parsed and reformatted  
- Custom error structures extracted  
- Offline detection based on message pattern matching

**Risk:** 
- Non-standard error responses might not display correctly  
- Error messages might be truncated or combined

**Remediation:** 
- Standardize backend error response format  
- Add error code constants  
- Test error scenarios systematically

### Issue #7: Run Markdown Snapshot Optional
**Location:** [runs.py](backend/app/api/v1/runs.py) GET `/{run_id}/markdown`

**Issue:** 
- Frontend calls `api.getRunMarkdown(runId)` in [RecentRunsCard.jsx](frontend/src/components/RecentRunsCard.jsx#L73)  
- Backend returns 404 if snapshot_path is empty or missing  
- No graceful fallback in frontend

**Impact:** 
- RecentRunsCard crashes if markdown not available  
- User sees error instead of "no snapshot available"

**Remediation:**
- Backend: Return empty markdown object instead of 404  
- Frontend: Handle missing markdown gracefully  
- Add UI indicator for "snapshot not yet generated"

### Issue #8: Export Format List from Backend Not Used
**Location:** [scraping_types.py](backend/app/api/v1/scraping_types.py) vs ExportManagementPanel

**Issue:** 
- Backend defines supported scraping types  
- No `/exports/formats` endpoint to list export formats  
- Frontend hardcodes export formats

**Risk:** 
- Adding new export format requires frontend code change  
- Format validation only at server (user sees HTTP error)

**Remediation:**
- Create `GET /exports/formats` endpoint  
- Frontend fetches and displays available formats  
- Client-side format validation

### Issue #9: Async Export Status Not Polled
**Location:** [exports.py](backend/app/api/v1/exports.py), [ExportManagementPanel.jsx](frontend/src/components/ExportManagementPanel.jsx)

**Issue:**
- Export creation is async (dispatches Celery task)  
- Initial response returns export with empty/pending file_path  
- Frontend doesn't poll for completion status

**Impact:** 
- User creates export, sees it immediately but file not ready  
- Clicking download too fast fails  
- No user feedback on actual generation progress

**Remediation:**
- Add polling for export status  
- Show "generating" state with progress  
- Disable download until status is "completed"

### Issue #10: Activity Feed Type Misalignment
**Location:** [user.py](backend/app/api/v1/user.py) GET `/user/activity`

**Frontend:** [ActivityTimeline.jsx](frontend/src/components/ActivityTimeline.jsx) expects activity data structure

**Issue:**
- Backend returns Dict[str, Any] with no schema  
- Frontend component expects specific data structure  
- No validation of response format

**Risk:**
- Implicit contract between frontend/backend  
- Breaking changes go undetected

**Remediation:**
- Add Pydantic schema for activity response  
- Frontend validates expected fields  
- Document activity data model

---

## 6. AUTHENTICATION & SECURITY FINDINGS

### Security Implementations ✅
1. **Password Hashing:** Using hash_password() and verify_password() [auth.py](backend/app/api/v1/auth.py#L49)
2. **JWT Tokens:** Bearer token-based authentication
3. **Request ID Tracking:** X-Request-ID header for observability [main.py](backend/app/main.py#L87)
4. **Security Headers:** CSP, X-Frame-Options, Referrer-Policy, etc.
5. **API Key Support:** Optional API key header authentication
6. **User Ownership Verification:** All endpoints check Job.user_id matches current_user

### Security Gaps ⚠️
1. **No Refresh Tokens:** JWT tokens don't rotate; indefinite validity
2. **No Token Revocation:** Deleted API keys still work until token expiry
3. **No Rate Limiting per User:** Generic rate limiting doesn't prevent account abuse
4. **Password Requirements:** No validation on password strength [auth.py](backend/app/api/v1/auth.py#L35)
5. **No 2FA:** No second factor authentication implemented
6. **Session Fixation:** No session binding to IP/user agent

### Recommended Security Improvements
1. Implement refresh token rotation
2. Add password complexity validation
3. Implement user-specific rate limits
4. Add 2FA support
5. Add IP-based rate limiting
6. Implement token blacklist for logout
7. Add login attempt tracking and lockout

---

## 7. DATA CONSISTENCY FINDINGS

### Data Normalization Issues

**Run Normalization in Frontend** ([api.js Line 176-187](frontend/src/services/api.js#L176-L187))
- Frontend normalizes `token_compression_ratio` to number
- Frontend normalizes `stealth_engaged` to boolean  
- Frontend normalizes `markdown_snapshot_path` to null if empty

**Impact:** Data transformation happens in frontend instead of backend serialization

**Consistency:** ✅ Works but ideally done in backend schemas

### Return Type Inconsistencies

**Export List Response:**
- Backend returns: `{exports: [], total: number}`
- Frontend expects: Array wrapped in object

**Run Response:**
- Backend normalizes run before returning
- Frontend normalizes again (double transformation)

**Recommendation:** Implement consistent return patterns:
- Always return paginated: `{items: [], total: number, limit: number, offset: number}`
- Normalize data once in backend schemas

---

## 8. PERFORMANCE & OPTIMIZATION FINDINGS

### Dashboard Performance Issue
**Location:** [DashboardPage.jsx](frontend/src/pages/DashboardPage.jsx#L83-L99)

**Issue:** 
```javascript
const [jobItems, runItems, summaryData] = await Promise.all([
  api.getJobs(),        // Get ALL jobs
  api.getRuns(),        // Get ALL runs  
  api.getAccountSummary()
])
// Then fetches results for latest run
const latestResults = await api.getResults(mostRecentRun.id)
```

**Problem:**
- Fetches all runs for dashboard overview  
- Only displays recent runs  
- Should use pagination or limit query parameter

**Recommendation:**
- `api.getRuns({limit: 10})` - Get only recent
- Add skip/limit parameters to all list endpoints

### Export Download Performance
**Location:** [exports.py](backend/app/api/v1/exports.py#L282-L384)

**Issue:** 
```python
for export_id in export_ids:
    # Validates each export individually
    stmt = select(Export).where(Export.id == export_id, ...)
```

**Problem:**
- N+1 query issue for multiple export validation  
- Each export requires separate database query

**Recommendation:**
- Batch validate: `select(Export).where(Export.id.in_(export_ids))`

---

## 9. API DOCUMENTATION GAPS

### Missing Documentation
1. **Error Response Format:** No consistent documented schema
2. **Pagination:** Not documented (uses skip/limit pattern)
3. **Date Format:** ISO 8601 assumed but not documented
4. **Large File Handling:** No docs on upload/download limits
5. **Concurrency:** No docs on handling simultaneous job runs
6. **Retry Behavior:** No docs on automatic retry vs. manual retry

### Missing Endpoint Documentation
1. `DELETE /jobs/{job_id}` - Not used in frontend, undocumented
2. `/user/history/{item_id}` - item_type parameter not validated
3. Export ZIP creation - Incomplete implementation not documented
4. `/demo/overview` - No schema documentation
5. `/system/diagnostics` - No response schema

---

## 10. SUMMARY TABLE: Frontend to Backend Coverage

| Category | Total Backend | Frontend Used | Coverage % | Issues |
|----------|---------------|---------------|-----------|--------|
| Auth | 3 endpoints | 3 | 100% | ✅ Complete |
| Account | 3 endpoints | 3 | 100% | ✅ Complete |
| User | 7 endpoints | 7 | 100% | ⚠️ Duplicate routes |
| Jobs | 6 endpoints | 5 | 83% | ❌ Missing delete |
| Runs | 6 endpoints | 6 | 100% | ✅ Complete |
| Results | 1 endpoint | 1 | 100% | ✅ Complete |
| Exports | 5 endpoints | 4 | 80% | ❌ ZIP incomplete |
| API Keys | 3 endpoints | 3 | 100% | ✅ Complete |
| Credentials | 3 endpoints | 3 | 100% | ✅ Complete |
| Scraping Types | 1 endpoint | 0 | 0% | ⚠️ Not used |
| System | 1 endpoint | 1 | 100% | ✅ Complete |
| Demo | 1 endpoint | 1 | 100% | ✅ Complete |
| **TOTAL** | **40 endpoints** | **36 endpoints** | **90%** | **4 gaps** |

---

## ACTIONABLE RECOMMENDATIONS

### Priority 1: CRITICAL (Complete immediately)
- [ ] Fix ZIP export implementation ([exports.py Line 335](backend/app/api/v1/exports.py#L335))
- [ ] Add export status polling to frontend  
- [ ] Implement job deletion in UI  
- [ ] Fix duplicate route decorators in user.py

### Priority 2: HIGH (Complete within sprint)
- [ ] Implement run cancellation endpoint  
- [ ] Implement export deletion endpoint  
- [ ] Add export status polling mechanism  
- [ ] Fix run markdown 404 error handling  
- [ ] Add password strength validation

### Priority 3: MEDIUM (Complete within 2 sprints)
- [ ] Add job update/patch endpoint  
- [ ] Create `/exports/formats` endpoint  
- [ ] Implement refresh token rotation  
- [ ] Fix N+1 query in export validation  
- [ ] Add user-specific rate limiting
- [ ] Standardize error response format

### Priority 4: LOW (Nice to have)
- [ ] Create `/demo/overview` response schema  
- [ ] Add logout endpoint with token blacklist  
- [ ] Implement bulk export features  
- [ ] Add pagination documentation  
- [ ] Create OpenAPI schema documentation

---

**End of Audit Report**
