import axios from 'axios';

const isLocalDevHost =
  typeof window !== 'undefined' &&
  ['localhost', '127.0.0.1'].includes(window.location.hostname);

const API_BASE_URL =
  process.env.REACT_APP_API_URL ||
  (isLocalDevHost ? 'http://127.0.0.1:8001/api/v1' : '/api/v1');
export const API_KEY_HEADER_NAME = process.env.REACT_APP_API_KEY_HEADER_NAME || 'X-API-Key';
const STATIC_API_KEY = (process.env.REACT_APP_API_KEY || '').trim();
const LOCAL_DEV_BOOTSTRAP_API_KEY = (process.env.REACT_APP_LOCAL_DEV_BOOTSTRAP_API_KEY || 'dev-api-key-change-me').trim();
const SESSION_API_KEY_STORAGE_KEY = 'smart_scraper_api_key';

const readSessionApiKey = () => {
  if (typeof window === 'undefined') {
    return '';
  }
  try {
    return (window.sessionStorage?.getItem(SESSION_API_KEY_STORAGE_KEY) || '').trim();
  } catch {
    return '';
  }
};

const storeSessionApiKey = (value) => {
  const normalized = String(value || '').trim();
  if (typeof window === 'undefined' || !normalized) {
    return;
  }
  try {
    window.sessionStorage?.setItem(SESSION_API_KEY_STORAGE_KEY, normalized);
  } catch {
    // Ignore storage failures and continue without session API-key persistence.
  }
};

const clearSessionApiKey = () => {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.sessionStorage?.removeItem(SESSION_API_KEY_STORAGE_KEY);
    window.localStorage?.removeItem(SESSION_API_KEY_STORAGE_KEY);
  } catch {
    // Ignore storage failures and continue.
  }
};

const resolveRequestApiKey = () => {
  if (STATIC_API_KEY) {
    return STATIC_API_KEY;
  }

  const sessionKey = readSessionApiKey();
  if (sessionKey) {
    return sessionKey;
  }

  if (isLocalDevHost) {
    return LOCAL_DEV_BOOTSTRAP_API_KEY;
  }

  return '';
};

const resolveRootApiUrl = () => {
  if (typeof API_BASE_URL === 'string' && /^https?:\/\//i.test(API_BASE_URL)) {
    return API_BASE_URL.replace(/\/api\/v1\/?$/i, '');
  }
  return '';
};

const resolveOfflineApiMessage = () => {
  if (typeof API_BASE_URL === 'string' && /^https?:\/\//i.test(API_BASE_URL)) {
    return `Cannot reach the API server at ${API_BASE_URL}. Start the backend and try again.`;
  }
  return 'Cannot reach the API server. Start the backend and try again.';
};

const extractValidationMessage = (detail) => {
  if (!Array.isArray(detail)) {
    return '';
  }

  const message = detail
    .map((item) => item?.msg || item?.message || '')
    .filter(Boolean)
    .join(' ');

  return message.trim();
};

const extractNestedErrorMessage = (payload) => {
  const message = payload?.error?.message;
  const trimmedMessage = typeof message === 'string' ? message.trim() : '';
  if (trimmedMessage && !/^request validation failed\.?$/i.test(trimmedMessage)) {
    return trimmedMessage;
  }

  const validationErrors = payload?.error?.details?.errors;
  if (!Array.isArray(validationErrors) || validationErrors.length === 0) {
    return trimmedMessage;
  }

  const firstUsefulMessage = validationErrors
    .map((item) => {
      const rawMessage = typeof item?.msg === 'string' ? item.msg.trim() : '';
      if (!rawMessage) {
        return '';
      }

      const lastLocationPart = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : '';
      if (typeof lastLocationPart === 'string' && lastLocationPart.trim()) {
        const fieldName = lastLocationPart.replace(/_/g, ' ');
        return `${fieldName.charAt(0).toUpperCase()}${fieldName.slice(1)}: ${rawMessage}`;
      }

      return `${rawMessage.charAt(0).toUpperCase()}${rawMessage.slice(1)}`;
    })
    .find(Boolean);

  return firstUsefulMessage || trimmedMessage;
};

const extractDetailMessage = (detail) => {
  if (typeof detail === 'string') {
    return detail.trim();
  }
  return extractValidationMessage(detail);
};

const extractApiErrorMessage = (error, fallback = 'An error occurred') => {
  const payload = error?.response?.data;
  const detailMessage = extractDetailMessage(payload?.detail);
  if (detailMessage) {
    return detailMessage;
  }

  const directMessage = typeof payload?.message === 'string' ? payload.message.trim() : '';
  if (directMessage) {
    return directMessage;
  }

  const nestedErrorMessage = extractNestedErrorMessage(payload);
  if (nestedErrorMessage) {
    return nestedErrorMessage;
  }

  if (!error?.response) {
    if (typeof error?.message === 'string' && error.message.trim()) {
      const trimmedMessage = error.message.trim();
      if (/network error|failed to fetch/i.test(trimmedMessage)) {
        return resolveOfflineApiMessage();
      }
      return trimmedMessage;
    }
    return resolveOfflineApiMessage();
  }

  return fallback;
};

const isLegacyLinkedPageWorkersValidationError = (error) => {
  const detail = error?.response?.data?.detail;
  if (!Array.isArray(detail)) {
    return false;
  }

  return detail.some((item) => {
    const loc = Array.isArray(item?.loc) ? item.loc.map((part) => String(part || '')) : [];
    const type = String(item?.type || '').trim().toLowerCase();
    const message = String(item?.msg || '').trim().toLowerCase();
    return (
      loc.includes('linked_page_workers') &&
      (type === 'extra_forbidden' || message.includes('extra inputs are not permitted'))
    );
  });
};

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

apiClient.interceptors.request.use(
  (config) => {
    config.headers = config.headers || {};
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    const apiKey = resolveRequestApiKey();
    if (apiKey) {
      config.headers[API_KEY_HEADER_NAME] = apiKey;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail || '';
    const requestUrl = String(error.config?.url || '');
    const isLoginRequest = requestUrl.includes('/auth/login');
    const normalizedDetail = String(detail || '').trim().toLowerCase();
    const isCredentialFailure =
      normalizedDetail === 'could not validate credentials'
      || normalizedDetail === 'inactive user account';

    if (
      error.response?.status === 401 &&
      (
        requestUrl.includes('/auth/me')
        || isCredentialFailure
      )
    ) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');

      // Avoid an unnecessary full-page redirect when the user is already
      // submitting credentials on /auth/login and just needs inline feedback.
      if (!isLoginRequest && typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }

    const message = extractApiErrorMessage(error);
    console.error('API Error:', message);

    return Promise.reject(error);
  }
);

const unwrapData = (promise) => promise.then((response) => response.data);

const normalizeRun = (run) => {
  if (!run || typeof run !== 'object') {
    return run;
  }

  const rawCompressionRatio = Number(run.token_compression_ratio);
  const hasCompressionRatio = Number.isFinite(rawCompressionRatio);
  const snapshotPath = typeof run.markdown_snapshot_path === 'string'
    ? run.markdown_snapshot_path.trim()
    : '';

  return {
    ...run,
    token_compression_ratio: hasCompressionRatio ? rawCompressionRatio : null,
    stealth_engaged: Boolean(run.stealth_engaged),
    markdown_snapshot_path: snapshotPath || null,
  };
};

const normalizeRuns = (runs) => (Array.isArray(runs) ? runs.map(normalizeRun) : []);

const CORE_EXECUTION_AGENTS = [
  'policy_service',
  'strategic_execution_service',
  'multi_source_service',
  'quality_layer',
  'event_emitter',
  'control_service',
];

const OPTIONAL_EXECUTION_AGENTS = ['analysis_agent', 'vector_agent', 'export_agent'];
const SUPPORTED_SOURCES = ['internal', 'google_maps', 'web'];

const inferDefaultSources = (job = null) => {
  const config = job && typeof job === 'object' && job.config && typeof job.config === 'object'
    ? job.config
    : {};
  const configuredSources = Array.isArray(config.sources) ? config.sources : [];
  const cleanedConfiguredSources = configuredSources
    .map((item) => String(item || '').trim())
    .filter((item) => SUPPORTED_SOURCES.includes(item));

  if (cleanedConfiguredSources.length > 0) {
    return [...new Set(cleanedConfiguredSources)];
  }

  const configuredSourceType = String(config.source_type || '').trim();
  if (SUPPORTED_SOURCES.includes(configuredSourceType)) {
    return [configuredSourceType];
  }

  const hasConcreteUrl = typeof job?.url === 'string' && job.url.trim().length > 0;
  if (hasConcreteUrl) {
    return ['web'];
  }

  return [...SUPPORTED_SOURCES];
};

const clampExecutionLimit = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 50;
  return Math.max(1, Math.min(100, Math.round(parsed)));
};

const sanitizeSources = (value) => {
  const values = Array.isArray(value) ? value : [];
  const cleaned = values
    .map((item) => String(item || '').trim())
    .filter((item) => SUPPORTED_SOURCES.includes(item));
  return cleaned.length > 0 ? [...new Set(cleaned)] : [];
};

const sanitizeOptionalAgents = (value) => {
  const values = Array.isArray(value) ? value : [];
  const cleaned = values
    .map((item) => String(item || '').trim())
    .filter((item) => OPTIONAL_EXECUTION_AGENTS.includes(item));
  return [...new Set(cleaned)];
};

const buildExecutionContractFromJob = (job = null) => {
  const config = job && typeof job === 'object' && job.config && typeof job.config === 'object'
    ? job.config
    : {};
  const sources = sanitizeSources(config.sources).length > 0
    ? sanitizeSources(config.sources)
    : inferDefaultSources(job);
  const limit = clampExecutionLimit(config.max_records ?? config.limit ?? 50);
  const controls = config.execution_controls && typeof config.execution_controls === 'object'
    ? config.execution_controls
    : {};

  return {
    agents: [...CORE_EXECUTION_AGENTS],
    optional_agents: sanitizeOptionalAgents(config.optional_agents),
    execution_mode: sources.length === 1 ? 'single_source' : 'multi_source',
    sources,
    limit,
    controls: {
      fallback: Boolean(controls.fallback ?? true),
      early_stop: Boolean(controls.early_stop ?? true),
      retry: Boolean(controls.retry ?? true),
    },
  };
};

const normalizeExecutionContract = (contract, job = null) => {
  const source = contract && typeof contract === 'object' ? contract : buildExecutionContractFromJob(job);
  const sources = sanitizeSources(source.sources).length > 0
    ? sanitizeSources(source.sources)
    : inferDefaultSources(job);
  const controls = source.controls && typeof source.controls === 'object' ? source.controls : {};

  return {
    agents: [...CORE_EXECUTION_AGENTS],
    optional_agents: sanitizeOptionalAgents(source.optional_agents),
    execution_mode: sources.length === 1 ? 'single_source' : 'multi_source',
    sources,
    limit: clampExecutionLimit(source.limit),
    controls: {
      fallback: Boolean(controls.fallback ?? true),
      early_stop: Boolean(controls.early_stop ?? true),
      retry: Boolean(controls.retry ?? true),
    },
  };
};

const parseDownloadFilename = (contentDisposition) => {
  if (typeof contentDisposition !== 'string' || !contentDisposition.trim()) {
    return '';
  }

  const utf8Match = contentDisposition.match(/filename\*\s*=\s*([^;]+)/i);
  if (utf8Match?.[1]) {
    const raw = utf8Match[1].trim().replace(/^UTF-8''/i, '').replace(/^["']|["']$/g, '');
    try {
      return decodeURIComponent(raw).replace(/[\\/]/g, '_');
    } catch {
      return raw.replace(/[\\/]/g, '_');
    }
  }

  const plainMatch = contentDisposition.match(/filename\s*=\s*"([^"]+)"/i)
    || contentDisposition.match(/filename\s*=\s*([^;]+)/i);
  if (!plainMatch?.[1]) {
    return '';
  }
  return plainMatch[1].trim().replace(/^["']|["']$/g, '').replace(/[\\/]/g, '_');
};

const toDownloadPayload = (response, fallbackFilename = 'download') => {
  const blob = response?.data instanceof Blob
    ? response.data
    : new Blob([response?.data ?? '']);
  const dispositionHeader = response?.headers?.['content-disposition'] || response?.headers?.['Content-Disposition'];
  const filename = parseDownloadFilename(dispositionHeader) || fallbackFilename;
  return { blob, filename };
};

const api = {
  login: (email, password) => {
    const normalizedEmail = String(email || '').trim().toLowerCase();
    const formData = new URLSearchParams();
    formData.set('username', normalizedEmail);
    formData.set('password', password);
    return unwrapData(
      apiClient.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
    );
  },

  register: (userData) => unwrapData(apiClient.post('/auth/register', userData)),

  getCurrentUser: () => unwrapData(apiClient.get('/auth/me')),

  getAccountSummary: () => unwrapData(apiClient.get('/account/summary')),

  getUsage: () => unwrapData(apiClient.get('/account/usage')),

  getPlan: () => unwrapData(apiClient.get('/account/plan')),

  getStorageCleanupSummary: () => unwrapData(apiClient.get('/user/storage-summary')),

  clearHistory: () => unwrapData(apiClient.delete('/user/history')),

  clearTempFiles: () => unwrapData(apiClient.delete('/user/temp-files')),

  clearAllUserData: () => unwrapData(apiClient.delete('/user/clear-all')),

  getUserActivity: (params = {}) =>
    unwrapData(apiClient.get('/user/activity', { params })),

  getUserHistory: (params = {}) =>
    unwrapData(apiClient.get('/user/history', { params })),

  deleteHistoryItem: (itemId, itemType) =>
    unwrapData(apiClient.delete(`/user/history/${itemId}`, { params: { item_type: itemType } })),

  getDashboardPreferences: () =>
    unwrapData(apiClient.get('/user/preferences/dashboard')),

  updateDashboardPreferences: (preferences) =>
    unwrapData(apiClient.put('/user/preferences/dashboard', preferences)),

  getDemoOverview: () => unwrapData(apiClient.get('/demo/overview')),

  getSystemDiagnostics: () => unwrapData(apiClient.get('/system/diagnostics')),
  getSystemCapabilities: () => unwrapData(apiClient.get('/system/capabilities')),

  refineScrapeRequest: (payload) => unwrapData(apiClient.post('/assistant/request-refinement', payload)),

  runScrape: (payload) => unwrapData(apiClient.post('/scrape', payload)),

  downloadMultipleExports: (exportIds) =>
    apiClient
      .post('/exports/download', exportIds, { responseType: 'blob' })
      .then((response) => {
        const fallback = exportIds.length === 1
          ? `export_${exportIds[0]}`
          : `bulk_export_${exportIds.length}_files.zip`;
        return toDownloadPayload(response, fallback);
      }),

  getApiKeys: (params = {}) =>
    unwrapData(apiClient.get('/api-keys', { params })).then((data) => data.api_keys || []),

  createApiKey: (payload) => unwrapData(apiClient.post('/api-keys', payload)),

  deleteApiKey: (apiKeyId) => unwrapData(apiClient.delete(`/api-keys/${apiKeyId}`)),

  getCredentials: (params = {}) =>
    unwrapData(apiClient.get('/credentials', { params })).then((data) => data.credentials || []),

  saveCredential: (payload) => unwrapData(apiClient.post('/credentials', payload)),

  deleteCredential: (provider) => unwrapData(apiClient.delete(`/credentials/${provider}`)),

  getSystemKeys: () =>
    unwrapData(apiClient.get('/system-keys')).then((data) => data.secrets || []),

  saveSystemKey: (name, payload) =>
    unwrapData(apiClient.put(`/system-keys/${name}`, payload)),

  deleteSystemKey: (name) =>
    unwrapData(apiClient.delete(`/system-keys/${name}`)),

  getJobs: (params = {}) =>
    unwrapData(apiClient.get('/jobs', { params })).then((data) => data.jobs || []),

  getJob: (jobId) => unwrapData(apiClient.get(`/jobs/${jobId}`)),

  createJob: async (jobData) => {
    try {
      return await unwrapData(apiClient.post('/jobs', jobData));
    } catch (error) {
      const config = jobData?.config;
      if (
        isLegacyLinkedPageWorkersValidationError(error) &&
        config &&
        Object.prototype.hasOwnProperty.call(config, 'linked_page_workers')
      ) {
        const fallbackPayload = {
          ...jobData,
          config: {
            ...config,
          },
        };
        delete fallbackPayload.config.linked_page_workers;
        return unwrapData(apiClient.post('/jobs', fallbackPayload));
      }
      throw error;
    }
  },

  deleteJob: (jobId) => unwrapData(apiClient.delete(`/jobs/${jobId}`)),
  deleteJobPermanently: (jobId) => unwrapData(apiClient.delete(`/jobs/${jobId}/permanent`)),

  startJobRun: async (jobId, options = {}) => {
    const explicitContract = options.execution_contract || options.executionContract || null;
    let jobSnapshot = options.job || null;

    if (!explicitContract && !jobSnapshot) {
      jobSnapshot = await unwrapData(apiClient.get(`/jobs/${jobId}`));
    }

    const payload = {
      execution_contract: normalizeExecutionContract(explicitContract, jobSnapshot),
    };

    return unwrapData(apiClient.post(`/jobs/${jobId}/runs`, payload)).then((run) => normalizeRun(run));
  },

  getRuns: (params = {}) =>
    unwrapData(apiClient.get('/runs', { params })).then((data) => normalizeRuns(data.runs)),

  getRun: (runId) => unwrapData(apiClient.get(`/runs/${runId}`)).then((run) => normalizeRun(run)),

  getRunLogs: (runId) =>
    unwrapData(apiClient.get(`/runs/${runId}/logs`)).then((data) => data.logs || []),

  getRunsByJob: (jobId, params = {}) =>
    unwrapData(apiClient.get(`/jobs/${jobId}/runs`, { params })).then((data) => normalizeRuns(data.runs)),

  retryRun: (runId) => unwrapData(apiClient.post(`/runs/${runId}/retry`)).then((run) => normalizeRun(run)),

  getRunMarkdown: (runId) => unwrapData(apiClient.get(`/runs/${runId}/markdown`)),

  getResults: (runId, params = {}) =>
    unwrapData(apiClient.get(`/runs/${runId}/results`, { params })).then((data) => data.results || []),

  createExport: (payload) => unwrapData(apiClient.post('/exports', payload)),

  getExports: (params = {}) =>
    unwrapData(apiClient.get('/exports', { params })).then((data) => data.exports || []),

  getExportStats: () => unwrapData(apiClient.get('/exports/stats')),

  downloadExport: (exportId) =>
    apiClient
      .get(`/exports/${exportId}/download`, { responseType: 'blob' })
      .then((response) => toDownloadPayload(response, `export_${exportId}`)),

  getScrapingTypes: () => unwrapData(apiClient.get('/scraping-types')),

  cancelRun: (runId) => unwrapData(apiClient.post(`/runs/${runId}/cancel`)),

  deleteExport: (exportId) => unwrapData(apiClient.delete(`/exports/${exportId}`)),

  getExportStatus: (exportId) => unwrapData(apiClient.get(`/exports/${exportId}`)),

  getHealth: () => {
    const rootApiUrl = resolveRootApiUrl();
    if (rootApiUrl) {
      return unwrapData(axios.get(`${rootApiUrl}/health`, { timeout: 10000 }));
    }
    return unwrapData(axios.get('/health', { timeout: 10000 }));
  },
};

export default api;
export { apiClient, extractApiErrorMessage, storeSessionApiKey, clearSessionApiKey };
