import React, { useCallback, useEffect, useRef, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import api from '../services/api';
import { EmptyState, PageHeader, PrimaryButton, Section } from './ui';

const focusClass = 'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950';

const ExportManagementPanel = () => {
  const [exports, setExports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [selectedExports, setSelectedExports] = useState([]);
  const [deletingIds, setDeletingIds] = useState(new Set());
  const pollingIntervals = useRef({});

  const stopStatusPolling = useCallback((exportId) => {
    const interval = pollingIntervals.current[exportId];
    if (interval) {
      clearInterval(interval);
      delete pollingIntervals.current[exportId];
    }
  }, []);

  const startStatusPolling = useCallback((exportId) => {
    if (pollingIntervals.current[exportId]) return;

    const interval = setInterval(async () => {
      try {
        const updatedExport = await api.getExportStatus(exportId);
        setExports((previous) => previous.map((item) => (item.id === exportId ? updatedExport : item)));

        if (updatedExport.status === 'completed' || updatedExport.status === 'failed') {
          stopStatusPolling(exportId);
        }
      } catch {
        stopStatusPolling(exportId);
      }
    }, 3000);

    pollingIntervals.current[exportId] = interval;
  }, [stopStatusPolling]);

  const loadExports = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getExports({ limit: 50 });
      const items = data || [];
      setExports(items);
      setError('');

      items.forEach((item) => {
        if (item.status === 'generating' || item.status === 'pending') {
          startStatusPolling(item.id);
        } else {
          stopStatusPolling(item.id);
        }
      });
    } catch {
      setError('Failed to load exports.');
    } finally {
      setLoading(false);
    }
  }, [startStatusPolling, stopStatusPolling]);

  useEffect(() => {
    loadExports();
    const intervalRegistry = pollingIntervals.current;

    return () => {
      Object.values(intervalRegistry).forEach((interval) => clearInterval(interval));
    };
  }, [loadExports]);

  const triggerDownload = (download, fallbackFilename) => {
    const blob = download?.blob instanceof Blob ? download.blob : new Blob([download?.blob ?? '']);
    const filename = String(download?.filename || fallbackFilename || 'download').trim() || 'download';
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(anchor);
  };

  const handleDownload = async (exportId) => {
    try {
      const download = await api.downloadExport(exportId);
      triggerDownload(download, `export_${exportId}`);
      setNotice(`Export ${exportId} downloaded.`);
    } catch {
      setError('Failed to download export.');
    }
  };

  const handleDelete = async (exportId) => {
    const confirmed = typeof window === 'undefined' || window.confirm('Delete this export?');
    if (!confirmed) return;

    try {
      setDeletingIds((previous) => new Set([...previous, exportId]));
      await api.deleteExport(exportId);
      setExports((previous) => previous.filter((item) => item.id !== exportId));
      setSelectedExports((previous) => previous.filter((itemId) => itemId !== exportId));
      stopStatusPolling(exportId);
      setNotice('Export deleted.');
    } catch {
      setError('Failed to delete export.');
    } finally {
      setDeletingIds((previous) => {
        const next = new Set(previous);
        next.delete(exportId);
        return next;
      });
    }
  };

  const handleBulkDownload = async () => {
    if (selectedExports.length === 0) return;

    try {
      const download = await api.downloadMultipleExports(selectedExports);
      const fallback = selectedExports.length === 1
        ? `export_${selectedExports[0]}`
        : `bulk_export_${selectedExports.length}_files.zip`;
      triggerDownload(download, fallback);
      setNotice(`${selectedExports.length} exports downloaded.`);
    } catch {
      setError('Failed to download selected exports.');
    }
  };

  const toggleExportSelection = (exportId) => {
    setSelectedExports((previous) =>
      previous.includes(exportId)
        ? previous.filter((id) => id !== exportId)
        : [...previous, exportId]
    );
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'text-emerald-200 bg-emerald-500/10 border-emerald-500/20';
      case 'generating':
      case 'pending':
        return 'text-amber-200 bg-amber-500/10 border-amber-500/20';
      case 'failed':
        return 'text-red-200 bg-red-500/10 border-red-500/20';
      default:
        return 'text-slate-300 bg-slate-800 border-white/10';
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const index = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${Math.round((bytes / (1024 ** index)) * 100) / 100} ${sizes[index]}`;
  };

  return (
    <section className="space-y-4">
      <PageHeader
        title="Exports"
        description="Download, monitor, and clean up generated export files."
        actions={selectedExports.length > 0 ? (
          <PrimaryButton type="button" onClick={handleBulkDownload}>
            Download Selected ({selectedExports.length})
          </PrimaryButton>
        ) : null}
      />

      {(error || notice) && (
        <div
          className={`rounded-xl border px-3 py-2 text-sm ${
            error ? 'border-red-400/30 bg-red-400/10 text-red-200' : 'border-emerald-500/25 bg-emerald-500/10 text-emerald-200'
          }`}
          role={error ? 'alert' : 'status'}
        >
          {error || notice}
        </div>
      )}

      <Section title="Export management" description="Track status, download complete files, and remove old exports.">
        {loading ? (
          <div className="animate-pulse space-y-3">
            {[...Array(3)].map((_, index) => (
              <div key={index} className="rounded-2xl border border-white/10 bg-slate-900 p-4">
                <div className="mb-2 h-4 w-1/3 rounded bg-white/10" />
                <div className="h-3 w-1/2 rounded bg-white/10" />
              </div>
            ))}
          </div>
        ) : exports.length === 0 ? (
          <EmptyState
            title="No exports found."
            description="Create an export from a run result and it will appear here."
          />
        ) : (
          <div className="space-y-3">
            {exports.map((exportItem) => (
              <div key={exportItem.id} className="rounded-2xl border border-white/10 bg-slate-900 p-4 transition hover:border-accent/30">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex min-w-[240px] flex-1 items-start gap-3">
                    <input
                      type="checkbox"
                      aria-label={`Select export ${exportItem.id}`}
                      checked={selectedExports.includes(exportItem.id)}
                      onChange={() => toggleExportSelection(exportItem.id)}
                      className={`mt-1 h-4 w-4 rounded border-white/20 bg-slate-950 ${focusClass}`}
                    />

                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-slate-100">{exportItem.job_name || 'Unknown job'}</span>
                        <span className={`rounded-full border px-2 py-1 text-xs font-medium ${getStatusColor(exportItem.status)}`}>
                          {String(exportItem.status || exportItem.format || '').toUpperCase()}
                        </span>
                      </div>
                      <div className="mt-1 text-sm text-slate-400">
                        Created {formatDistanceToNow(new Date(exportItem.created_at), { addSuffix: true })}
                        {exportItem.file_size && exportItem.status === 'completed' ? (
                          <span className="ml-2">• {formatFileSize(exportItem.file_size)}</span>
                        ) : null}
                      </div>
                    </div>
                  </div>

                  <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
                    {exportItem.status === 'completed' && (
                      <button
                        type="button"
                        onClick={() => handleDownload(exportItem.id)}
                        className={`w-full rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-sm text-emerald-200 transition hover:border-emerald-400 sm:w-auto ${focusClass}`}
                      >
                        Download
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDelete(exportItem.id)}
                      disabled={deletingIds.has(exportItem.id)}
                      className={`w-full rounded-lg border border-red-400/30 bg-red-400/10 px-3 py-1 text-sm text-red-200 transition hover:border-red-300 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto ${focusClass}`}
                    >
                      {deletingIds.has(exportItem.id) ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>
    </section>
  );
};

export default ExportManagementPanel;
