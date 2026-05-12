import React, { useMemo, useState } from 'react';
import { formatDate, formatStatus } from '../utils/helpers';

const STEP_ORDER = ['intake', 'scraper', 'processing', 'vector', 'analysis', 'export'];

const STEP_LABELS = {
  intake: 'Understanding request',
  scraper: 'Collecting pages',
  processing: 'Cleaning and structuring records',
  vector: 'Matching similar content',
  analysis: 'Generating summary',
  export: 'Preparing final output',
};

const isFailureEntry = (entry) => {
  const event = String(entry?.event || '').toLowerCase();
  const level = String(entry?.level || '').toLowerCase();
  return event.includes('failed') || event.includes('timeout') || level === 'error';
};

const getStepTone = (status) => {
  if (status === 'completed') return 'text-emerald-300';
  if (status === 'failed') return 'text-red-300';
  if (status === 'active') return 'text-sky-300';
  return 'text-slate-500';
};

const parseSourceSummary = (results = []) => {
  const first = results[0];
  const payload = first?.data_json && typeof first.data_json === 'object' ? first.data_json : {};

  const items = Array.isArray(payload.items)
    ? payload.items
    : Array.isArray(payload.result?.processed?.items)
      ? payload.result.processed.items
      : Array.isArray(payload.data)
        ? payload.data
        : [];

  const sourceCount = Array.isArray(payload.sources)
    ? payload.sources.length
    : Array.isArray(payload.links)
      ? payload.links.length
      : 0;

  const confidence = Number(payload.execution?.validation?.confidence);
  const summaryText =
    payload.summary
    || payload.insights?.summary
    || (items.length > 0 ? `Collected ${items.length} record(s).` : 'Run completed. Open results for full details.');

  return {
    summaryText,
    itemCount: items.length,
    sourceCount,
    confidence: Number.isFinite(confidence) ? confidence : null,
  };
};

export const buildNodeState = (logs = [], overallStatus = '') => {
  const state = STEP_ORDER.reduce((accumulator, step) => {
    accumulator[step] = 'pending';
    return accumulator;
  }, {});

  const normalizedLogs = Array.isArray(logs) ? logs : [];
  const terminalFailureIndex =
    ['failed', 'cancelled', 'canceled'].includes(String(overallStatus).toLowerCase())
      ? normalizedLogs.findIndex((entry) => isFailureEntry(entry))
      : -1;
  const logsToApply = terminalFailureIndex >= 0
    ? normalizedLogs.slice(0, terminalFailureIndex + 1)
    : normalizedLogs;

  logsToApply.forEach((entry) => {
    const node = String(entry?.details?.node || '').toLowerCase();
    if (!STEP_ORDER.includes(node)) return;

    if (entry.event === 'node_started') {
      state[node] = 'active';
    }
    if (entry.event === 'node_completed') {
      state[node] = 'completed';
    }
    if (entry.event === 'node_failed' || entry.event === 'node_timeout') {
      state[node] = 'failed';
    }
  });

  if (terminalFailureIndex >= 0) {
    STEP_ORDER.forEach((step) => {
      if (state[step] === 'active') {
        state[step] = 'failed';
      }
    });
  }

  return state;
};

const latestFailure = (run, logs = []) => {
  const fromLogs = [...logs].reverse().find((entry) => {
    const event = String(entry?.event || '').toLowerCase();
    return event.includes('failed') || event.includes('timeout') || String(entry?.level || '').toLowerCase() === 'error';
  });

  return fromLogs?.message || run?.error_message || '';
};

const friendlyFailureMessage = (message) => {
  if (!message) return '';
  if (/timeout/i.test(message)) return 'This run took too long while waiting for a website response.';
  if (/forbidden|401|403/i.test(message)) return 'Access was blocked by the target site. Check login settings and try again.';
  if (/invalid|validation/i.test(message)) return 'Some request details were invalid. Update advanced settings and retry.';
  return message;
};

const RunProgressCard = ({ run, logs = [], results = [], systemHealth = null }) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const stepState = useMemo(() => buildNodeState(logs, run?.status), [logs, run?.status]);
  const completed = STEP_ORDER.filter((step) => stepState[step] === 'completed');
  const active = STEP_ORDER.find((step) => stepState[step] === 'active');
  const failed = STEP_ORDER.find((step) => stepState[step] === 'failed');
  const summary = parseSourceSummary(results);
  const progress = Number(run?.progress || 0);
  const failureMessage = friendlyFailureMessage(latestFailure(run, logs));
  const queueState = String(systemHealth?.services?.queue || 'unknown');
  const redisState = String(systemHealth?.services?.redis || 'unknown');
  const workerState = queueState === 'ok' ? 'ready' : queueState === 'unavailable' ? 'offline' : 'unknown';

  if (!run) {
    return null;
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-slate-100">Run Progress</h2>
        <span className="rounded-full border border-white/10 bg-slate-900 px-2 py-1 text-xs text-slate-300">
          {formatStatus(run.status)}
        </span>
      </div>

      <div className="mt-3 space-y-2" role="status" aria-live="polite">
        <div className="flex items-center justify-between text-sm text-slate-300">
          <span>Active step: {failed ? STEP_LABELS[failed] : active ? STEP_LABELS[active] : 'Waiting'}</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div
          className="h-2 overflow-hidden rounded-full bg-slate-800"
          role="progressbar"
          aria-valuenow={Math.round(progress)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Run progress"
        >
          <div className="h-full bg-sky-500 transition-all" style={{ width: `${Math.max(4, Math.min(progress, 100))}%` }} />
        </div>
        <p className="text-xs text-slate-400">
          Started {formatDate(run.started_at)}
          {run.finished_at ? ` • Finished ${formatDate(run.finished_at)}` : ''}
        </p>
      </div>

      <div className="mt-4">
        <h3 className="text-sm font-medium text-slate-200">Human-readable steps</h3>
        <ul className="mt-2 space-y-1 text-sm">
          {STEP_ORDER.map((step) => (
            <li key={step} className={`flex items-center justify-between rounded-lg border border-white/5 bg-slate-900/50 px-3 py-2 ${getStepTone(stepState[step])}`}>
              <span>{STEP_LABELS[step]}</span>
              <span className="text-xs uppercase tracking-wide">{stepState[step]}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-4">
        <h3 className="text-sm font-medium text-slate-200">Completed steps</h3>
        {completed.length === 0 ? (
          <p className="mt-1 text-sm text-slate-400">Completed steps will appear as the run advances.</p>
        ) : (
          <div className="mt-2 flex flex-wrap gap-2">
            {completed.map((step) => (
              <span key={step} className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-200">
                {STEP_LABELS[step]}
              </span>
            ))}
          </div>
        )}
      </div>

      {failureMessage && (
        <div className="mt-4 rounded-xl border border-red-400/30 bg-red-400/10 px-3 py-2 text-sm text-red-200">
          <p className="font-medium">Friendly error message</p>
          <p className="mt-1">{failureMessage}</p>
        </div>
      )}

      {String(run.status).toLowerCase() === 'completed' && (
        <div className="mt-4 rounded-xl border border-white/10 bg-slate-900 p-3 text-sm text-slate-300">
          <p className="font-medium text-slate-200">Final output summary</p>
          <p className="mt-1">{summary.summaryText}</p>
          <p className="mt-1 text-xs text-slate-400">
            Records: {summary.itemCount} • Sources: {summary.sourceCount}
            {summary.confidence !== null ? ` • Confidence: ${Math.round(summary.confidence * 100)}%` : ''}
          </p>
        </div>
      )}

      <div className="mt-4 rounded-xl border border-white/10 bg-slate-900 p-3">
        <button
          type="button"
          onClick={() => setShowAdvanced((value) => !value)}
          className="text-sm font-medium text-slate-200 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950"
          aria-expanded={showAdvanced}
          aria-controls="run-progress-advanced-debug"
        >
          {showAdvanced ? 'Hide' : 'Show'} Advanced debug
        </button>

        {showAdvanced && (
          <div id="run-progress-advanced-debug" className="mt-3 space-y-2 text-xs text-slate-400">
            <p>
              Worker: <span className="text-slate-200">{workerState}</span> • Queue:{' '}
              <span className="text-slate-200">{queueState}</span> • Redis:{' '}
              <span className="text-slate-200">{redisState}</span>
            </p>

            <ul className="space-y-1">
              {[...logs].slice(-10).map((entry, index) => (
                <li key={`${entry.timestamp}-${entry.event}-${index}`} className="rounded-lg border border-white/5 bg-slate-950 px-2 py-1">
                  <span className="text-slate-300">{entry.event}</span>: {entry.message || '-'}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
};

export default RunProgressCard;
