import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { extractApiErrorMessage } from '../services/api';
import { formatDate, formatStatus } from '../utils/helpers';

const STATUS_FILTERS = ['all', 'pending', 'running', 'completed', 'failed'];
const focusClass = 'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950';

const tone = (status) => {
  const normalized = String(status || '').toLowerCase();
  if (normalized === 'completed') return 'border-emerald-500/25 bg-emerald-500/10 text-emerald-200';
  if (normalized === 'failed') return 'border-red-400/25 bg-red-400/10 text-red-200';
  if (normalized === 'running' || normalized === 'pending') return 'border-sky-500/25 bg-sky-500/10 text-sky-200';
  return 'border-white/10 bg-slate-800 text-slate-200';
};

const HistoryList = () => {
  const navigate = useNavigate();
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('all');
  const [busyRunId, setBusyRunId] = useState('');

  const loadRuns = async () => {
    try {
      setLoading(true);
      const data = await api.getRuns({ limit: 100 });
      setRuns(data || []);
      setError('');
    } catch (runError) {
      setError(extractApiErrorMessage(runError, 'Could not load run history.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const filtered = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    return runs.filter((run) => {
      const matchesStatus = status === 'all' || String(run.status).toLowerCase() === status;
      if (!matchesStatus) return false;
      if (!normalizedSearch) return true;

      return [run.id, run.job_id, run.status]
        .map((value) => String(value || '').toLowerCase())
        .some((value) => value.includes(normalizedSearch));
    });
  }, [runs, search, status]);

  const handleRetry = async (runId) => {
    if (!runId || busyRunId) return;

    try {
      setBusyRunId(runId);
      await api.retryRun(runId);
      await loadRuns();
    } catch (retryError) {
      setError(extractApiErrorMessage(retryError, 'Could not retry this run.'));
    } finally {
      setBusyRunId('');
    }
  };

  const handleCopyRunId = async (runId) => {
    if (!navigator.clipboard || !runId) return;
    await navigator.clipboard.writeText(String(runId));
  };

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1 space-y-1 text-sm">
          <label htmlFor="history-search" className="text-slate-400">
            Search runs
          </label>
          <input
            id="history-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by run ID, job ID, or status"
            className={`w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-slate-100 placeholder:text-slate-500 ${focusClass}`}
          />
        </div>

        <div className="space-y-1 text-sm">
          <label htmlFor="history-status" className="text-slate-400">
            Status
          </label>
          <select
            id="history-status"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className={`rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-slate-100 ${focusClass}`}
          >
            {STATUS_FILTERS.map((option) => (
              <option key={option} value={option}>
                {option === 'all' ? 'All statuses' : formatStatus(option)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <div className="rounded-xl border border-red-400/30 bg-red-400/10 px-3 py-2 text-sm text-red-200">{error}</div>}

      <div className="rounded-2xl border border-white/10 bg-slate-950">
        {loading ? (
          <p className="px-4 py-8 text-center text-sm text-slate-400">Loading runs...</p>
        ) : filtered.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-slate-400">No runs match your filters.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-white/10 text-sm">
              <thead className="bg-slate-900/70">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-slate-300">Run</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-300">Job</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-300">Status</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-300">Progress</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-300">Started</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-300">Quick actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filtered.map((run) => (
                  <tr key={run.id} className="hover:bg-slate-900/40">
                    <td className="px-3 py-2 text-slate-200">#{run.id}</td>
                    <td className="px-3 py-2 text-slate-300">{run.job_id || '-'}</td>
                    <td className="px-3 py-2">
                      <span className={`rounded-full border px-2 py-1 text-xs ${tone(run.status)}`}>
                        {formatStatus(run.status)}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-300">{Math.round(Number(run.progress || 0))}%</td>
                    <td className="px-3 py-2 text-slate-400">{formatDate(run.started_at)}</td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => navigate(`/workspace/${run.job_id || ''}`)}
                          className={`rounded-lg border border-white/10 bg-slate-900 px-2 py-1 text-xs text-slate-200 transition hover:border-slate-500 ${focusClass}`}
                        >
                          Open
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRetry(run.id)}
                          disabled={busyRunId === run.id}
                          className={`rounded-lg border border-white/10 bg-slate-900 px-2 py-1 text-xs text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60 ${focusClass}`}
                        >
                          {busyRunId === run.id ? 'Retrying...' : 'Retry'}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleCopyRunId(run.id)}
                          className={`rounded-lg border border-white/10 bg-slate-900 px-2 py-1 text-xs text-slate-200 transition hover:border-slate-500 ${focusClass}`}
                        >
                          Copy ID
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
};

export default HistoryList;
