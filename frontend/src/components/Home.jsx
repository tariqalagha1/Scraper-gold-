import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AdvancedOptionsPanel from './AdvancedOptionsPanel';
import RunProgressCard from './RunProgressCard';
import ResultsPage from './ResultsPage';
import { PageHeader, PrimaryButton, Section } from './ui';
import api, { extractApiErrorMessage } from '../services/api';
import { detectScrapeType } from '../assistant/orchestrator';

const splitFields = (value) =>
  String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

const clampLimit = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 50;
  return Math.max(1, Math.min(500, Math.floor(numeric)));
};

const clampMaxPages = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 10;
  return Math.max(1, Math.min(1000, Math.floor(numeric)));
};

const clampLinkedPageLimit = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 20;
  return Math.max(1, Math.min(1000, Math.floor(numeric)));
};

const clampLinkedPageWorkers = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 4;
  return Math.max(1, Math.min(16, Math.floor(numeric)));
};

const isValidHttpUrl = (value) => {
  try {
    const parsed = new URL(String(value || '').trim());
    return ['http:', 'https:'].includes(parsed.protocol);
  } catch {
    return false;
  }
};

const normalizePotentialUrl = (value) => {
  const raw = String(value || '').trim().replace(/[),.;!?]+$/, '');
  if (!raw) return '';
  if (isValidHttpUrl(raw)) return raw;
  const withProtocol = `https://${raw.replace(/^\/+/, '')}`;
  return isValidHttpUrl(withProtocol) ? withProtocol : '';
};

const URL_PATTERN = /((?:https?:\/\/|www\.)[^\s]+|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:\/[^\s]*)?)/i;
const LANDING_INTENT_KEY = 'landing_extraction_intent';
const focusClass = 'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950';

const extractUrlFromCommand = (command) => {
  const text = String(command || '').trim();
  if (!text) return '';
  const match = text.match(URL_PATTERN);
  if (!match) return '';
  return normalizePotentialUrl(match[1]);
};

const stripUrlFromCommand = (command, normalizedUrl) => {
  const text = String(command || '').trim();
  if (!text) return '';
  const urlWithoutProtocol = String(normalizedUrl || '').replace(/^https?:\/\//i, '');

  return text
    .replace(String(normalizedUrl || ''), ' ')
    .replace(urlWithoutProtocol, ' ')
    .replace(/\s+/g, ' ')
    .trim();
};

const deriveLocationFromCommand = (command, fallback = 'Saudi Arabia') => {
  const text = String(command || '').trim();
  if (!text) return fallback;

  const match = text.match(
    /\b(?:in|at|near)\s+([a-zA-Z][a-zA-Z\s-]{1,80}?)(?=\s+(?:with|for|and|that|from)\b|[.,]|$)/i
  );

  if (!match || !match[1]) return fallback;
  const location = match[1].replace(/\s+/g, ' ').trim();
  return location || fallback;
};

const deriveFieldsFromCommand = (command, fallbackFields = ['name', 'contact', 'email']) => {
  const text = String(command || '').toLowerCase();
  const inferred = new Set(fallbackFields.map((item) => String(item).trim()).filter(Boolean));

  if (/\bname|names|company|business|clinic|hospital\b/.test(text)) inferred.add('name');
  if (/\bemail|emails|e-mail\b/.test(text)) inferred.add('email');
  if (/\bphone|mobile|contact|number|whatsapp\b/.test(text)) inferred.add('contact');
  if (/\bwebsite|url|domain|link\b/.test(text)) inferred.add('website');
  if (/\baddress|location\b/.test(text)) inferred.add('address');

  return Array.from(inferred).slice(0, 50);
};

const toSourcesArray = (value) => {
  if (!Array.isArray(value)) return [];

  return value
    .map((item) => {
      if (!item || typeof item !== 'object') return null;
      const name = String(item.name || '').trim();
      const count = Number(item.count);
      if (!name) return null;

      return {
        name,
        count: Number.isFinite(count) && count >= 0 ? Math.floor(count) : 0,
      };
    })
    .filter(Boolean);
};

const toRecordsArray = (value) => {
  if (!Array.isArray(value)) return [];
  return value.filter((item) => item && typeof item === 'object');
};

const normalizeScrapeResponse = (payload, fallbackRequestId) => {
  if (payload && typeof payload === 'object' && payload.output_payload) {
    const output = payload.output_payload || {};
    const quality = output.quality || {};
    const metadata = payload.metadata || {};
    const summary = payload.summary || {};

    return {
      request_id: String(
        metadata.request_id || output.request_id || payload.request_id || fallbackRequestId || ''
      ),
      status: String(payload.status || output.status || 'failed').toLowerCase(),
      execution_time: Number(metadata.execution_time ?? output.execution_time ?? payload.execution_time ?? 0) || 0,
      total: Number(summary.total ?? output.total ?? 0) || 0,
      data: toRecordsArray(output.data),
      sources: toSourcesArray(output.sources),
      errors: Array.isArray(output.errors) ? output.errors.map(String) : [],
      quality: {
        duplicates_removed: Number(quality.duplicates_removed || 0) || 0,
        coverage: Number(quality.coverage || 0) || 0,
        confidence: Number(quality.confidence || 0) || 0,
        missing_fields:
          quality.missing_fields && typeof quality.missing_fields === 'object' ? quality.missing_fields : {},
      },
      insights: payload.insights || null,
      raw: payload,
    };
  }

  const quality = payload?.quality || {};
  const data = toRecordsArray(payload?.data);

  return {
    request_id: String(payload?.request_id || fallbackRequestId || ''),
    status: String(payload?.status || 'failed').toLowerCase(),
    execution_time: Number(payload?.execution_time || 0) || 0,
    total: Number(payload?.total ?? data.length) || 0,
    data,
    sources: toSourcesArray(payload?.sources),
    errors: Array.isArray(payload?.errors) ? payload.errors.map(String) : [],
    quality: {
      duplicates_removed: Number(quality.duplicates_removed || 0) || 0,
      coverage: Number(quality.coverage || 0) || 0,
      confidence: Number(quality.confidence || 0) || 0,
      missing_fields:
        quality.missing_fields && typeof quality.missing_fields === 'object' ? quality.missing_fields : {},
    },
    insights: payload?.insights || null,
    raw: payload,
  };
};

const buildFallbackInsights = (result) => {
  const total = Number(result.total || 0);
  const sources = Array.isArray(result.sources) ? result.sources : [];
  const coverage = Math.max(0, Math.min(1, Number(result.quality?.coverage || 0)));
  const confidence = Math.max(0, Math.min(1, Number(result.quality?.confidence || 0)));

  return {
    summary:
      total > 0
        ? `Found ${total} records across ${sources.length} source${sources.length === 1 ? '' : 's'}.`
        : 'No matching records were found for this query.',
    key_findings: [
      `Coverage is ${Math.round(coverage * 100)}%.`,
      `Confidence is ${Math.round(confidence * 100)}%.`,
      sources[0] ? `Top source: ${sources[0].name}.` : 'No source breakdown was returned.',
    ],
    data_quality_note:
      confidence >= 0.75 && coverage >= 0.75
        ? 'Data quality is strong for immediate use.'
        : 'Review critical fields before making decisions.',
    recommended_next_step:
      total === 0
        ? 'Try broadening your query and run again.'
        : 'Use export to share this data, then run a focused follow-up if needed.',
  };
};

const resolveInsights = (normalizedResult) => {
  const rawInsights = normalizedResult?.insights;
  if (
    rawInsights
    && typeof rawInsights === 'object'
    && typeof rawInsights.summary === 'string'
    && Array.isArray(rawInsights.key_findings)
    && typeof rawInsights.data_quality_note === 'string'
    && typeof rawInsights.recommended_next_step === 'string'
  ) {
    return {
      summary: rawInsights.summary,
      key_findings: rawInsights.key_findings.map(String).slice(0, 5),
      data_quality_note: rawInsights.data_quality_note,
      recommended_next_step: rawInsights.recommended_next_step,
    };
  }

  return buildFallbackInsights(normalizedResult);
};

const flattenRunResults = (results = []) => {
  const rows = [];

  results.forEach((result) => {
    const payload = result?.data_json && typeof result.data_json === 'object' ? result.data_json : {};
    if (Array.isArray(payload.items) && payload.items.length > 0) {
      payload.items.forEach((item) => {
        if (item && typeof item === 'object') rows.push(item);
      });
      return;
    }

    if (Array.isArray(payload.data) && payload.data.length > 0) {
      payload.data.forEach((item) => {
        if (item && typeof item === 'object') rows.push(item);
      });
      return;
    }

    if (Object.keys(payload).length > 0) {
      rows.push(payload);
    }
  });

  return rows;
};

const toWebsiteResult = (run, results, logs) => {
  const firstPayload = results[0]?.data_json && typeof results[0].data_json === 'object' ? results[0].data_json : {};
  const rows = flattenRunResults(results);

  const validation = firstPayload.execution?.validation || {};
  const confidence = Number(validation.confidence);
  const quality = {
    confidence: Number.isFinite(confidence) ? confidence : 0,
    coverage: rows.length > 0 ? 1 : 0,
    duplicates_removed: 0,
    missing_fields: firstPayload.quality?.missing_fields || {},
  };

  const sources = Array.isArray(firstPayload.sources)
    ? firstPayload.sources
    : Array.isArray(firstPayload.links)
      ? firstPayload.links.map((link) => ({ name: String(link), count: 1 }))
      : [];

  const errorMessages = [
    ...(Array.isArray(firstPayload.errors) ? firstPayload.errors.map(String) : []),
    ...(run?.error_message ? [String(run.error_message)] : []),
    ...logs
      .filter((entry) => String(entry?.level || '').toLowerCase() === 'error')
      .map((entry) => String(entry?.message || '').trim())
      .filter(Boolean),
  ];

  const normalized = {
    request_id: String(run?.id || ''),
    status: String(run?.status || 'failed').toLowerCase(),
    execution_time: Number(run?.duration_seconds || 0),
    total: rows.length,
    data: rows,
    sources,
    errors: errorMessages,
    quality,
    insights: firstPayload.insights || null,
    raw: { run, results, logs },
  };

  return {
    ...normalized,
    insights: resolveInsights(normalized),
  };
};

const csvEscape = (value) => {
  const normalized = value === null || value === undefined ? '' : String(value);
  if (normalized.includes('"') || normalized.includes(',') || normalized.includes('\n')) {
    return `"${normalized.replace(/"/g, '""')}"`;
  }
  return normalized;
};

const downloadAsCsv = (rows, fileName = 'smart-scraper-results.csv') => {
  if (!Array.isArray(rows) || rows.length === 0) return;

  const columns = Array.from(
    rows.reduce((keys, row) => {
      Object.keys(row || {}).forEach((key) => keys.add(key));
      return keys;
    }, new Set())
  );

  const lines = [columns.map(csvEscape).join(',')];

  rows.forEach((row) => {
    const line = columns.map((column) => csvEscape(row?.[column])).join(',');
    lines.push(line);
  });

  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.setAttribute('download', fileName);
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
};

const makeSyntheticLogs = (state = 'running', errorMessage = '') => {
  const now = Date.now();
  const stamp = (offset) => new Date(now + offset).toISOString();

  if (state === 'failed') {
    return [
      { event: 'node_started', details: { node: 'intake' }, message: 'Understanding request', timestamp: stamp(-5000) },
      { event: 'node_completed', details: { node: 'intake' }, message: 'Request validated', timestamp: stamp(-4000) },
      { event: 'node_started', details: { node: 'scraper' }, message: 'Collecting source records', timestamp: stamp(-3000) },
      { event: 'node_failed', details: { node: 'scraper' }, message: errorMessage || 'Data collection failed', timestamp: stamp(-1000) },
    ];
  }

  if (state === 'completed') {
    return [
      { event: 'node_started', details: { node: 'intake' }, message: 'Understanding request', timestamp: stamp(-7000) },
      { event: 'node_completed', details: { node: 'intake' }, message: 'Request validated', timestamp: stamp(-6000) },
      { event: 'node_started', details: { node: 'scraper' }, message: 'Collecting source records', timestamp: stamp(-5000) },
      { event: 'node_completed', details: { node: 'scraper' }, message: 'Collection complete', timestamp: stamp(-3500) },
      { event: 'node_started', details: { node: 'processing' }, message: 'Cleaning records', timestamp: stamp(-3000) },
      { event: 'node_completed', details: { node: 'processing' }, message: 'Records structured', timestamp: stamp(-2000) },
      { event: 'node_started', details: { node: 'analysis' }, message: 'Generating summary', timestamp: stamp(-1500) },
      { event: 'node_completed', details: { node: 'analysis' }, message: 'Summary ready', timestamp: stamp(-500) },
    ];
  }

  return [
    { event: 'node_started', details: { node: 'intake' }, message: 'Understanding request', timestamp: stamp(-3000) },
    { event: 'node_completed', details: { node: 'intake' }, message: 'Request validated', timestamp: stamp(-2000) },
    { event: 'node_started', details: { node: 'scraper' }, message: 'Collecting source records', timestamp: stamp(-1000) },
  ];
};

const Home = () => {
  const navigate = useNavigate();

  const [workspace, setWorkspace] = useState({
    requestText: '',
    targetUrl: '',
    location: 'Saudi Arabia',
    limit: 50,
    maxPages: 10,
    followPagination: true,
    pageExpansionMode: 'same_domain',
    linkedPageLimit: 20,
    linkedPageWorkers: 4,
    linkedPageKeywords: 'price, product, user, details',
    fieldsText: 'name, contact, email',
    requiresLogin: false,
    loginUrl: '',
    loginUsername: '',
    loginPassword: '',
  });

  const [runState, setRunState] = useState({
    status: 'idle',
    mode: 'structured',
    jobId: '',
    message: '',
    error: '',
  });

  const [run, setRun] = useState(null);
  const [logs, setLogs] = useState([]);
  const [runResults, setRunResults] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [result, setResult] = useState(null);
  const [copyMessage, setCopyMessage] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') return;

    try {
      const rawIntent = window.sessionStorage.getItem(LANDING_INTENT_KEY);
      if (!rawIntent) return;

      const parsed = JSON.parse(rawIntent);
      const prompt = String(parsed?.prompt || '').trim();
      const url = normalizePotentialUrl(parsed?.url || '');
      const requestText = [prompt, url].filter(Boolean).join(' ').trim();

      if (!requestText && !url) {
        window.sessionStorage.removeItem(LANDING_INTENT_KEY);
        return;
      }

      setWorkspace((previous) => ({
        ...previous,
        requestText: requestText || previous.requestText,
        targetUrl: url || previous.targetUrl,
        maxPages: Number.isFinite(Number(parsed?.max_pages)) ? clampMaxPages(parsed.max_pages) : previous.maxPages,
        followPagination:
          typeof parsed?.follow_pagination === 'boolean' ? parsed.follow_pagination : previous.followPagination,
        requiresLogin: Boolean(parsed?.requiresLogin || parsed?.login_url),
        loginUrl: String(parsed?.login_url || '').trim() || previous.loginUrl,
        loginUsername: String(parsed?.login_username || '').trim() || previous.loginUsername,
        loginPassword: String(parsed?.login_password || '').trim() || previous.loginPassword,
      }));
    } catch {
      // Ignore malformed intent payloads.
    } finally {
      window.sessionStorage.removeItem(LANDING_INTENT_KEY);
    }
  }, []);

  const modePreview = useMemo(() => {
    const requestUrl = extractUrlFromCommand(workspace.requestText);
    const explicitUrl = normalizePotentialUrl(workspace.targetUrl);
    const url = explicitUrl || requestUrl;
    return {
      mode: url ? 'website' : 'structured',
      url,
      hint: url
        ? 'Website mode detected. We will create a run and track pipeline execution.'
        : 'Structured mode detected. We will return clean records directly.',
    };
  }, [workspace.requestText, workspace.targetUrl]);

  const fetchRunArtifacts = useCallback(async (jobId) => {
    const [runs, health] = await Promise.all([
      api.getRunsByJob(jobId, { limit: 5 }),
      api.getHealth().catch(() => null),
    ]);

    const latestRun = runs[0] || null;
    if (!latestRun) return;

    setRun(latestRun);
    setSystemHealth(health);

    const [latestLogs, latestResults] = await Promise.all([
      api.getRunLogs(latestRun.id),
      api.getResults(latestRun.id),
    ]);

    setLogs(latestLogs || []);
    setRunResults(latestResults || []);

    const status = String(latestRun.status || '').toLowerCase();
    if (['completed', 'failed', 'cancelled', 'canceled'].includes(status)) {
      const nextStatus = status === 'completed' ? 'completed' : 'failed';
      setRunState((previous) => ({
        ...previous,
        status: nextStatus,
        message: nextStatus === 'completed' ? 'Run completed successfully.' : 'Run finished with issues.',
        error: nextStatus === 'failed' ? latestRun.error_message || previous.error : '',
      }));

      if (nextStatus === 'completed') {
        setResult(toWebsiteResult(latestRun, latestResults || [], latestLogs || []));
      }
    }
  }, []);

  useEffect(() => {
    if (runState.mode !== 'website' || runState.status !== 'running' || !runState.jobId) {
      return undefined;
    }

    fetchRunArtifacts(runState.jobId).catch(() => {
      setRunState((previous) => ({
        ...previous,
        status: 'failed',
        error: 'Could not fetch live run progress. Open Workspace for full details.',
      }));
    });

    const interval = window.setInterval(() => {
      fetchRunArtifacts(runState.jobId).catch(() => {
        setRunState((previous) => ({
          ...previous,
          status: 'failed',
          error: 'Could not fetch live run progress. Open Workspace for full details.',
        }));
      });
    }, 4000);

    return () => window.clearInterval(interval);
  }, [runState.mode, runState.status, runState.jobId, fetchRunArtifacts]);

  const resetOutputs = () => {
    setRun(null);
    setLogs([]);
    setRunResults([]);
    setSystemHealth(null);
    setResult(null);
    setCopyMessage('');
  };

  const handleRun = async () => {
    const command = String(workspace.requestText || '').trim();

    if (!command && !modePreview.url) {
      setRunState((previous) => ({
        ...previous,
        status: 'failed',
        error: 'Write your request first, then click Run.',
      }));
      return;
    }

    resetOutputs();

    try {
      if (modePreview.mode === 'website') {
        if (!isValidHttpUrl(modePreview.url)) {
          setRunState({
            status: 'failed',
            mode: 'website',
            jobId: '',
            message: '',
            error: 'Detected URL is invalid. Use a full URL like https://example.com.',
          });
          return;
        }

        const prompt = stripUrlFromCommand(command, modePreview.url) || command;
        const requestedLimit = clampLimit(workspace.limit);
        const jobPayload = {
          url: modePreview.url,
          prompt,
          scrape_type: detectScrapeType(prompt) || 'general',
          max_pages: clampMaxPages(workspace.maxPages),
          follow_pagination: Boolean(workspace.followPagination),
          config: {
            max_records: requestedLimit,
            page_expansion_mode: String(workspace.pageExpansionMode || 'same_domain'),
            linked_page_limit: clampLinkedPageLimit(workspace.linkedPageLimit),
            linked_page_workers: clampLinkedPageWorkers(workspace.linkedPageWorkers),
            linked_page_keywords: splitFields(workspace.linkedPageKeywords),
          },
          login_url: workspace.requiresLogin ? workspace.loginUrl || null : null,
          login_username: workspace.requiresLogin ? workspace.loginUsername || null : null,
          login_password: workspace.requiresLogin ? workspace.loginPassword || null : null,
        };

        setRunState({
          status: 'running',
          mode: 'website',
          jobId: '',
          message: 'Creating job and starting pipeline...',
          error: '',
        });

        const createdJob = await api.createJob(jobPayload);
        const startedRun = await api.startJobRun(createdJob.id, { job: createdJob });

        setRun(startedRun);
        setLogs(makeSyntheticLogs('running'));
        setRunState({
          status: 'running',
          mode: 'website',
          jobId: String(createdJob.id),
          message: 'Pipeline started. Tracking live run progress.',
          error: '',
        });

        return;
      }

      const requestId = `scrape-${Date.now()}`;
      const location = deriveLocationFromCommand(command, workspace.location);
      const defaultFields = splitFields(workspace.fieldsText);
      const fields = deriveFieldsFromCommand(command, defaultFields.length > 0 ? defaultFields : ['name', 'contact', 'email']);

      const payload = {
        query: command,
        location,
        limit: clampLimit(workspace.limit),
        fields,
        request_id: requestId,
      };

      const startedAt = new Date().toISOString();
      setRun({
        id: requestId,
        status: 'running',
        progress: 35,
        started_at: startedAt,
      });
      setLogs(makeSyntheticLogs('running'));
      setRunState({
        status: 'running',
        mode: 'structured',
        jobId: '',
        message: 'Running structured extraction...',
        error: '',
      });

      const rawResult = await api.runScrape(payload);
      const normalizedResult = normalizeScrapeResponse(rawResult, requestId);
      const finalResult = {
        ...normalizedResult,
        insights: resolveInsights(normalizedResult),
      };

      setRun({
        id: requestId,
        status: finalResult.status || 'completed',
        progress: 100,
        started_at: startedAt,
        finished_at: new Date().toISOString(),
        error_message: finalResult.errors?.[0] || '',
      });
      setLogs(makeSyntheticLogs('completed'));
      setResult(finalResult);
      setRunState({
        status: 'completed',
        mode: 'structured',
        jobId: '',
        message: 'Result ready.',
        error: '',
      });
    } catch (runError) {
      const message = extractApiErrorMessage(runError, 'Could not run this request.');
      setRun((previous) =>
        previous
          ? {
              ...previous,
              status: 'failed',
              progress: Math.max(10, Number(previous.progress || 10)),
              finished_at: new Date().toISOString(),
              error_message: message,
            }
          : null
      );
      setLogs(makeSyntheticLogs('failed', message));
      setRunState((previous) => ({
        ...previous,
        status: 'failed',
        error: message,
      }));
    }
  };

  const handleCopyResult = async () => {
    if (!result || !navigator.clipboard) return;

    const content = [
      result.insights?.summary || '',
      '',
      JSON.stringify(result.data || [], null, 2),
    ]
      .filter(Boolean)
      .join('\n');

    await navigator.clipboard.writeText(content);
    setCopyMessage('Copied result summary and records.');
    window.setTimeout(() => setCopyMessage(''), 2000);
  };

  const handleExportResult = () => {
    if (!result?.data || result.data.length === 0) return;
    downloadAsCsv(result.data, `smart-scraper-${Date.now()}.csv`);
  };

  const handleOpenWorkspace = () => {
    if (!runState.jobId) return;
    navigate(`/workspace/${runState.jobId}`);
  };

  return (
    <section className="space-y-4">
      <Section>
        <PageHeader
          title="Home"
          description="Single input. One run button. Advanced controls only when needed."
        />

        <div className="mt-4 space-y-3">
          <div className="block space-y-1 text-sm">
            <label htmlFor="home-request-input" className="text-slate-400">
              What do you want to scrape?
            </label>
            <textarea
              id="home-request-input"
              value={workspace.requestText}
              onChange={(event) => setWorkspace((previous) => ({ ...previous, requestText: event.target.value }))}
              placeholder="Example: Find clinics in Riyadh with phone numbers and emails"
              rows={4}
              className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 placeholder:text-slate-500 ${focusClass}`}
            />
          </div>

          <div className="rounded-xl border border-sky-500/20 bg-sky-500/10 px-3 py-2 text-sm text-sky-200" role="status">
            <span className="font-medium">Mode detection:</span> {modePreview.hint}
            {modePreview.url ? ` (${modePreview.url})` : ''}
          </div>

          <AdvancedOptionsPanel workspace={workspace} setWorkspace={setWorkspace} mode={modePreview.mode} />

          <div className="flex flex-wrap items-center gap-2">
            <PrimaryButton
              type="button"
              onClick={handleRun}
              disabled={runState.status === 'running'}
            >
              {runState.status === 'running' ? 'Running...' : 'Run'}
            </PrimaryButton>

            {runState.mode === 'website' && runState.jobId && runState.status === 'running' && (
              <button
                type="button"
                onClick={handleOpenWorkspace}
                className={`w-full rounded-xl border border-white/10 bg-slate-900 px-4 py-2 text-sm text-slate-200 transition hover:border-slate-500 sm:w-auto ${focusClass}`}
              >
                Open Workspace
              </button>
            )}
          </div>

          {runState.message && <p className="text-xs text-slate-400">{runState.message}</p>}
          {runState.error && (
            <div className="rounded-xl border border-red-400/30 bg-red-400/10 px-3 py-2 text-sm text-red-200" role="alert">
              {runState.error}
            </div>
          )}
          {copyMessage && (
            <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200" role="status">
              {copyMessage}
            </div>
          )}
        </div>
      </Section>

      {run && <RunProgressCard run={run} logs={logs} results={runResults} systemHealth={systemHealth} />}

      {result && (
        <ResultsPage
          result={result}
          onCopy={handleCopyResult}
          onExport={handleExportResult}
          onRerun={handleRun}
        />
      )}
    </section>
  );
};

export default Home;
