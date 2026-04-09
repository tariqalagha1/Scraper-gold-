const LANDING_EXTRACTION_INTENT_KEY = 'landing_extraction_intent';

const normalizeIntent = (value) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }

  const url = String(value.url || '').trim();
  if (!url) {
    return null;
  }

  return {
    url,
    prompt: String(value.prompt || '').trim(),
    scrape_type: value.scrape_type ? String(value.scrape_type).trim() : '',
    max_pages: Number.isFinite(Number(value.max_pages)) ? Math.max(1, Math.min(1000, Number(value.max_pages))) : 10,
    follow_pagination:
      value.follow_pagination === undefined ? true : Boolean(value.follow_pagination),
    requiresLogin: Boolean(value.requiresLogin),
    login_url: value.login_url ? String(value.login_url).trim() : '',
    login_username: value.login_username ? String(value.login_username).trim() : '',
    login_password: value.login_password ? String(value.login_password) : '',
  };
};

export const readLandingExtractionIntent = () => {
  if (typeof window === 'undefined' || !window.sessionStorage) {
    return null;
  }

  try {
    const raw = window.sessionStorage.getItem(LANDING_EXTRACTION_INTENT_KEY);
    if (!raw) {
      return null;
    }
    return normalizeIntent(JSON.parse(raw));
  } catch {
    return null;
  }
};

export const clearLandingExtractionIntent = () => {
  if (typeof window === 'undefined' || !window.sessionStorage) {
    return;
  }

  window.sessionStorage.removeItem(LANDING_EXTRACTION_INTENT_KEY);
};

export const storeLandingExtractionIntent = (value) => {
  if (typeof window === 'undefined' || !window.sessionStorage) {
    return;
  }

  const normalized = normalizeIntent(value);
  if (!normalized) {
    clearLandingExtractionIntent();
    return;
  }

  window.sessionStorage.setItem(LANDING_EXTRACTION_INTENT_KEY, JSON.stringify(normalized));
};

export const consumeLandingExtractionIntent = () => {
  const intent = readLandingExtractionIntent();
  clearLandingExtractionIntent();
  return intent;
};
