import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import api from '../services/api';
import { EmptyState, PageHeader, Section } from './ui';

const focusClass = 'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950';

const ExportStatusView = () => {
  const [exports, setExports] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchExportData = async () => {
      try {
        setLoading(true);
        const [exportItems, exportStats] = await Promise.all([api.getExports(), api.getExportStats()]);
        setExports(exportItems || []);
        setStats(exportStats || {});
        setError('');
      } catch (fetchError) {
        setError(fetchError?.response?.data?.detail || 'Could not load export status.');
      } finally {
        setLoading(false);
      }
    };

    fetchExportData();
  }, []);

  const handleDownload = async (exportId) => {
    try {
      const download = await api.downloadExport(exportId);
      const blob = download?.blob instanceof Blob ? download.blob : new Blob([download?.blob ?? '']);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = String(download?.filename || `export-${exportId}`).trim() || `export-${exportId}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(downloadError?.response?.data?.detail || 'Could not download export.');
    }
  };

  return (
    <section className="space-y-4">
      <PageHeader title="Export Status" description="Track export volume, formats, and downloadable files." />

      {error && (
        <div className="rounded-md border border-red-400/30 bg-red-400/10 px-4 py-2 text-sm text-red-200" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <Section title="Loading exports">
          <p className="text-sm text-slate-400">Loading exports...</p>
        </Section>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Section title="Total exports">
              <p className="text-2xl font-semibold text-slate-100">{stats.total_exports || 0}</p>
            </Section>
            <Section title="Total size">
              <p className="text-2xl font-semibold text-slate-100">
                {((Number(stats.total_size_bytes) || 0) / (1024 * 1024)).toFixed(1)} MB
              </p>
            </Section>
            <Section title="Formats">
              <p className="text-2xl font-semibold text-slate-100">{Object.keys(stats.formats || {}).length}</p>
            </Section>
          </div>

          <Section title="Export files" description="Download generated files by job and date.">
            {exports.length === 0 ? (
              <EmptyState title="No exports found." description="Generated exports will appear here." />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-white/10">
                  <thead className="bg-slate-900/70">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Job</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Format</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Size</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Date</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10 bg-slate-950">
                    {exports.map((exportItem) => (
                      <tr key={exportItem.id}>
                        <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-100">{exportItem.job_name}</td>
                        <td className="whitespace-nowrap px-4 py-3 text-sm capitalize text-slate-300">{exportItem.format}</td>
                        <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-400">{(exportItem.file_size / 1024).toFixed(1)} KB</td>
                        <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-400">{format(new Date(exportItem.created_at), 'MMM dd, yyyy')}</td>
                        <td className="whitespace-nowrap px-4 py-3 text-sm font-medium">
                          <button
                            type="button"
                            onClick={() => handleDownload(exportItem.id)}
                            className={`text-sky-300 hover:text-sky-200 ${focusClass}`}
                          >
                            Download
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>
        </>
      )}
    </section>
  );
};

export default ExportStatusView;
