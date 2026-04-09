import axios from 'axios';

const isLocalDevHost =
  typeof window !== 'undefined' &&
  ['localhost', '127.0.0.1'].includes(window.location.hostname);

const API_BASE_URL =
  process.env.REACT_APP_API_URL ||
  (isLocalDevHost ? 'http://127.0.0.1:8000/api/v1' : '/api/v1');

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

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
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

    if (
      error.response?.status === 401 &&
      (
        detail === 'Could not validate credentials' ||
        requestUrl.includes('/auth/me') ||
        requestUrl.includes('/auth/login')
      )
    ) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
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

const api = {
  login: (email, password) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    return unwrapData(
      apiClient.post('/auth/login', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    );
  },

  register: (userData) => unwrapData(apiClient.post('/auth/register', userData)),

  getCurrentUser: () => unwrapData(apiClient.get('/auth/me')),

  getAccountSummary: () => unwrapData(apiClient.get('/account/summary')),

  getUsage: () => unwrapData(apiClient.get('/account/usage')),

  getPlan: () => unwrapData(apiClient.get('/account/plan')),

  getApiKeys: (params = {}) =>
    unwrapData(apiClient.get('/api-keys', { params })).then((data) => data.api_keys || []),

  createApiKey: (payload) => unwrapData(apiClient.post('/api-keys', payload)),

  deleteApiKey: (apiKeyId) => unwrapData(apiClient.delete(`/api-keys/${apiKeyId}`)),

  getCredentials: (params = {}) =>
    unwrapData(apiClient.get('/credentials', { params })).then((data) => data.credentials || []),

  saveCredential: (payload) => unwrapData(apiClient.post('/credentials', payload)),

  deleteCredential: (provider) => unwrapData(apiClient.delete(`/credentials/${provider}`)),

  getJobs: (params = {}) =>
    unwrapData(apiClient.get('/jobs', { params })).then((data) => data.jobs || []),

  getJob: (jobId) => unwrapData(apiClient.get(`/jobs/${jobId}`)),

  createJob: (jobData) => unwrapData(apiClient.post('/jobs', jobData)),

  startJobRun: (jobId) =>
    unwrapData(apiClient.post(`/jobs/${jobId}/runs`)).then((run) => normalizeRun(run)),

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

  downloadExport: (exportId) =>
    apiClient
      .get(`/exports/${exportId}/download`, { responseType: 'blob' })
      .then((response) => response.data),

  getScrapingTypes: () => unwrapData(apiClient.get('/scraping-types')),

  getHealth: () => {
    const rootApiUrl = resolveRootApiUrl();
    if (rootApiUrl) {
      return unwrapData(axios.get(`${rootApiUrl}/health`, { timeout: 10000 }));
    }
    return unwrapData(axios.get('/health', { timeout: 10000 }));
  },
};

export default api;
export { apiClient, extractApiErrorMessage };
