const LOCAL_HISTORY_KEYS = ['recent_requests'];
const LOCAL_TEMP_SESSION_KEYS = ['landing_extraction_intent'];
const LOCAL_CACHE_KEYS = ['user'];
const LOCAL_AUTH_KEYS = ['access_token'];

const safeReadJsonArray = (key) => {
  try {
    const value = window.localStorage.getItem(key);
    const parsed = JSON.parse(value || '[]');
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const stringBytes = (value) => {
  try {
    return new TextEncoder().encode(String(value || '')).length;
  } catch {
    return String(value || '').length;
  }
};

export const getLocalCleanupEstimate = () => {
  if (typeof window === 'undefined') {
    return {
      historyEntries: 0,
      tempEntries: 0,
      cacheEntries: 0,
      estimatedBytes: 0,
    };
  }

  const recentRequests = safeReadJsonArray('recent_requests');
  const landingIntentRaw = window.sessionStorage?.getItem('landing_extraction_intent') || '';
  const cachedUser = window.localStorage?.getItem('user') || '';
  const accessToken = window.localStorage?.getItem('access_token') || '';

  return {
    historyEntries: recentRequests.length,
    tempEntries: landingIntentRaw ? 1 : 0,
    cacheEntries: [cachedUser, accessToken].filter(Boolean).length,
    estimatedBytes:
      stringBytes(JSON.stringify(recentRequests)) +
      stringBytes(landingIntentRaw) +
      stringBytes(cachedUser) +
      stringBytes(accessToken),
  };
};

const removeKeyAndMeasure = (store, key) => {
  const currentValue = store?.getItem(key);
  if (currentValue == null) {
    return { clearedEntries: 0, freedBytes: 0 };
  }

  const clearedEntries = (() => {
    try {
      const parsed = JSON.parse(currentValue);
      return Array.isArray(parsed) ? parsed.length || 1 : 1;
    } catch {
      return 1;
    }
  })();

  const freedBytes = stringBytes(currentValue);
  store.removeItem(key);
  return { clearedEntries, freedBytes };
};

export const clearAllLocalSessionArtifacts = () => {
  if (typeof window === 'undefined') {
    return { clearedEntries: 0, freedBytes: 0 };
  }

  let clearedEntries = 0;
  let freedBytes = 0;

  [...LOCAL_AUTH_KEYS, ...LOCAL_CACHE_KEYS, ...LOCAL_HISTORY_KEYS].forEach((key) => {
    const result = removeKeyAndMeasure(window.localStorage, key);
    clearedEntries += result.clearedEntries;
    freedBytes += result.freedBytes;
  });

  if (window.sessionStorage) {
    for (let index = 0; index < window.sessionStorage.length; index += 1) {
      const key = window.sessionStorage.key(index);
      if (!key) {
        continue;
      }
      const currentValue = window.sessionStorage.getItem(key);
      if (currentValue != null) {
        freedBytes += stringBytes(currentValue);
        clearedEntries += 1;
      }
    }
    window.sessionStorage.clear();
  }

  return { clearedEntries, freedBytes };
};

export const redirectToLogin = () => {
  if (typeof window === 'undefined') {
    return;
  }

  window.location.href = '/login';
};

export const clearLocalCleanupScope = (scope) => {
  if (typeof window === 'undefined') {
    return { clearedEntries: 0, freedBytes: 0 };
  }

  if (scope === 'all') {
    return clearAllLocalSessionArtifacts();
  }

  const keysToClear = new Set();

  if (scope === 'history') {
    LOCAL_HISTORY_KEYS.forEach((key) => keysToClear.add(`local:${key}`));
  }
  if (scope === 'temp') {
    LOCAL_TEMP_SESSION_KEYS.forEach((key) => keysToClear.add(`session:${key}`));
  }

  let clearedEntries = 0;
  let freedBytes = 0;

  keysToClear.forEach((qualifiedKey) => {
    const [bucket, key] = qualifiedKey.split(':');
    const store = bucket === 'session' ? window.sessionStorage : window.localStorage;
    const result = removeKeyAndMeasure(store, key);
    freedBytes += result.freedBytes;
    clearedEntries += result.clearedEntries;
  });

  return { clearedEntries, freedBytes };
};

export const bytesToMegabytes = (bytes) => Number((Number(bytes || 0) / (1024 * 1024)).toFixed(2));
