import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import SectionHeader from '../components/SectionHeader';
import api from '../services/api';
import {
  bytesToMegabytes,
  clearLocalCleanupScope,
  getLocalCleanupEstimate,
  redirectToLogin,
} from '../utils/storageCleanup';

const ACTIONS = {
  history: {
    title: 'Clear History',
    scope: 'history',
    buttonClass:
      'rounded-2xl border border-white/10 px-5 py-3 text-sm text-textMuted transition hover:border-accent/30 hover:text-textMain',
    description:
      'Delete search history, prompt history, previous runs, generated report metadata, and recent activity tied to your account.',
    warning:
      'Saved request history, run history, and report metadata will be removed for this account.',
    apiCall: () => api.clearHistory(),
  },
  temp: {
    title: 'Clear Temporary Files',
    scope: 'temp',
    buttonClass:
      'rounded-2xl border border-warning/30 px-5 py-3 text-sm text-warning transition hover:bg-warning/10',
    description:
      'Delete cached exports, temporary markdown, PDFs, image cache, backend processing files, and stale local temp storage.',
    warning:
      'Temporary files will be removed, and previews or downloads may need to be regenerated later.',
    apiCall: () => api.clearTempFiles(),
  },
  all: {
    title: 'Clear All',
    scope: 'all',
    buttonClass:
      'rounded-2xl bg-danger px-5 py-3 text-sm font-semibold text-white transition hover:brightness-110',
    description:
      'Delete both history and temporary files, and clear local cache keys and stale session artifacts on this device.',
    warning:
      'This clears all account history plus temporary storage. This action cannot be undone.',
    apiCall: () => api.clearAllUserData(),
  },
};

const formatMb = (value) => `${Number(value || 0).toFixed(2)} MB`;
const CLEAR_ALL_REDIRECT_DELAY_MS = 300;

const SettingsPage = () => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyScope, setBusyScope] = useState('');
  const [notice, setNotice] = useState({ type: '', message: '' });
  const [modalScope, setModalScope] = useState('');
  const localEstimate = useMemo(() => getLocalCleanupEstimate(), []);

  const loadSummary = async () => {
    try {
      setLoading(true);
      const response = await api.getStorageCleanupSummary();
      setSummary(response);
      setNotice((previous) => (previous.type === 'error' ? { type: '', message: '' } : previous));
    } catch (error) {
      setSummary(null);
      setNotice({ type: 'error', message: 'We could not load your storage cleanup estimate right now.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  const metricsByScope = useMemo(() => {
    const historyRecords = Number(summary?.history?.total_records || 0);
    const tempFiles = Number(summary?.temp_files?.total_files || 0);
    const backendFreedMb = Number(summary?.temp_files?.estimated_freed_space_mb || 0);
    const localFreedMb = bytesToMegabytes(localEstimate.estimatedBytes);

    return {
      history: {
        items: historyRecords + localEstimate.historyEntries,
        sizeMb: backendFreedMb + localFreedMb,
      },
      temp: {
        items: tempFiles + localEstimate.tempEntries,
        sizeMb: backendFreedMb + localFreedMb,
      },
      all: {
        items: historyRecords + tempFiles + localEstimate.historyEntries + localEstimate.tempEntries + localEstimate.cacheEntries,
        sizeMb: backendFreedMb + localFreedMb,
      },
    };
  }, [localEstimate, summary]);

  const handleConfirmAction = async () => {
    const action = ACTIONS[modalScope];
    if (!action || busyScope) {
      return;
    }

    try {
      setBusyScope(action.scope);
      const response = await action.apiCall();
      const localCleanup = clearLocalCleanupScope(action.scope);
      setModalScope('');
      setNotice({
        type: 'success',
        message: `${action.title} completed. Deleted ${response.deleted_items_count + localCleanup.clearedEntries} items and freed about ${formatMb(response.freed_space_mb + bytesToMegabytes(localCleanup.freedBytes))}.`,
      });
      if (action.scope === 'all') {
        window.setTimeout(() => {
          redirectToLogin();
        }, CLEAR_ALL_REDIRECT_DELAY_MS);
        return;
      }
      await loadSummary();
    } catch (error) {
      setNotice({
        type: 'error',
        message: error?.response?.data?.detail || `We could not complete "${action.title}" right now.`,
      });
    } finally {
      setBusyScope('');
    }
  };

  const activeAction = modalScope ? ACTIONS[modalScope] : null;
  const activeMetrics = modalScope ? metricsByScope[modalScope] : null;

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 lg:px-8">
      <SectionHeader
        eyebrow="Settings"
        title="Storage & Privacy"
        description="Review what can be safely removed from your account history and temporary storage, then clear it with an explicit confirmation step."
      />

      {notice.message && (
        <div
          className={`fixed right-6 top-28 z-40 max-w-md rounded-3xl border px-5 py-4 text-sm shadow-glow ${
            notice.type === 'error'
              ? 'border-danger/30 bg-danger/10 text-danger'
              : 'border-success/30 bg-success/10 text-success'
          }`}
        >
          {notice.message}
        </div>
      )}

      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <Link
          to="/ai-integrations"
          className="rounded-[24px] border border-white/10 bg-surface p-6 transition hover:border-accent/40"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent">Integrations</p>
          <h3 className="mt-3 text-2xl font-semibold text-textMain">AI Integrations</h3>
          <p className="mt-3 text-sm leading-6 text-textMuted">
            Manage provider API keys (OpenAI, Anthropic, Gemini, Serper) and encrypted backend integration state.
          </p>
        </Link>

        <Link
          to="/api-keys"
          className="rounded-[24px] border border-white/10 bg-surface p-6 transition hover:border-accent/40"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent">Features</p>
          <h3 className="mt-3 text-2xl font-semibold text-textMain">API Keys</h3>
          <p className="mt-3 text-sm leading-6 text-textMuted">
            Create and rotate Smart Scraper API keys used by your own scripts and external integrations.
          </p>
        </Link>
      </div>

      <div className="mt-10 grid gap-8 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-[28px] border border-white/10 bg-surface p-6 shadow-glow">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent">Path</p>
          <h3 className="mt-3 text-2xl font-semibold text-textMain">Settings → Storage & Privacy</h3>
          <p className="mt-3 text-sm leading-6 text-textMuted">
            Use these actions to clear account history, temporary backend artifacts, and local cache keys without affecting other users.
          </p>

          <div className="mt-6 space-y-4">
            <div className="rounded-[24px] border border-white/10 bg-bg/60 p-5">
              <p className="text-sm font-semibold text-textMain">History estimate</p>
              <p className="mt-2 text-sm text-textMuted">
                {loading ? 'Loading...' : `${metricsByScope.history.items} deletable history items`}
              </p>
            </div>
            <div className="rounded-[24px] border border-white/10 bg-bg/60 p-5">
              <p className="text-sm font-semibold text-textMain">Temporary files estimate</p>
              <p className="mt-2 text-sm text-textMuted">
                {loading ? 'Loading...' : `${metricsByScope.temp.items} temp items, about ${formatMb(metricsByScope.temp.sizeMb)}`}
              </p>
            </div>
            <div className="rounded-[24px] border border-accent/20 bg-accentSoft p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent">Safety</p>
              <p className="mt-3 text-sm leading-6 text-textMain">
                Deletion is scoped to the authenticated user, confirmed with an explicit modal, and recorded through backend audit logging.
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {Object.entries(ACTIONS).map(([key, action]) => (
            <div key={key} className="rounded-[28px] border border-white/10 bg-surface p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="max-w-2xl">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent">
                    {key === 'history' ? 'Clear History' : key === 'temp' ? 'Clear Temporary Files' : 'Clear All'}
                  </p>
                  <h3 className="mt-3 text-2xl font-semibold text-textMain">{action.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-textMuted">{action.description}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setModalScope(key)}
                  disabled={loading || busyScope === action.scope}
                  className={`${action.buttonClass} disabled:cursor-not-allowed disabled:opacity-60`}
                >
                  {busyScope === action.scope ? 'Working...' : action.title}
                </button>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-3">
                <div className="rounded-[20px] border border-white/10 bg-bg/60 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-textMuted">Items</p>
                  <p className="mt-2 text-2xl font-semibold text-textMain">{metricsByScope[key].items}</p>
                </div>
                <div className="rounded-[20px] border border-white/10 bg-bg/60 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-textMuted">Estimated Size</p>
                  <p className="mt-2 text-2xl font-semibold text-textMain">{formatMb(metricsByScope[key].sizeMb)}</p>
                </div>
                <div className="rounded-[20px] border border-white/10 bg-bg/60 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-textMuted">What Gets Deleted</p>
                  <p className="mt-2 text-sm leading-6 text-textMuted">
                    {key === 'history'
                      ? 'Searches, prompts, previous runs, report metadata, and activity history.'
                      : key === 'temp'
                        ? 'Cached exports, markdown, PDFs, screenshots, processing files, and stale temp storage.'
                        : 'Both history and temporary files, plus local cache keys and stale session artifacts.'}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {activeAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
          <div className="w-full max-w-2xl rounded-[32px] border border-white/10 bg-surface p-8 shadow-glow">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-danger">Are you sure?</p>
            <h3 className="mt-3 text-3xl font-semibold text-textMain">This action cannot be undone.</h3>
            <p className="mt-4 text-sm leading-7 text-textMuted">{activeAction.warning}</p>

            <div className="mt-6 rounded-[24px] border border-danger/20 bg-danger/10 p-5">
              <p className="text-sm font-semibold text-danger">Warning message</p>
              <p className="mt-2 text-sm leading-6 text-textMuted">
                Clearing this scope permanently removes account data and local cached artifacts associated with it.
              </p>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-[22px] border border-white/10 bg-bg/60 p-5">
                <p className="text-xs uppercase tracking-[0.2em] text-textMuted">File Size Estimate</p>
                <p className="mt-2 text-2xl font-semibold text-textMain">{formatMb(activeMetrics?.sizeMb || 0)}</p>
              </div>
              <div className="rounded-[22px] border border-white/10 bg-bg/60 p-5">
                <p className="text-xs uppercase tracking-[0.2em] text-textMuted">Deleted Items Count</p>
                <p className="mt-2 text-2xl font-semibold text-textMain">{activeMetrics?.items || 0}</p>
              </div>
            </div>

            <div className="mt-8 flex flex-wrap justify-end gap-3">
              <button
                type="button"
                onClick={() => setModalScope('')}
                className="rounded-2xl border border-white/10 px-5 py-3 text-sm text-textMuted transition hover:border-white/20 hover:text-textMain"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmAction}
                disabled={busyScope === activeAction.scope}
                className="rounded-2xl bg-danger px-5 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {busyScope === activeAction.scope ? 'Deleting...' : activeAction.title}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SettingsPage;
