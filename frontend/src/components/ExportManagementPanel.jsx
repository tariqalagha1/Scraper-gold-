import React, { useState, useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';
import api from '../services/api';

const ExportManagementPanel = () => {
  const [exports, setExports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedExports, setSelectedExports] = useState([]);

  useEffect(() => {
    loadExports();
  }, []);

  const loadExports = async () => {
    try {
      setLoading(true);
      const data = await api.getExports({ limit: 50 });
      setExports(data || []);
    } catch (err) {
      setError('Failed to load exports');
      console.error('Error loading exports:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (exportId) => {
    try {
      const blob = await api.downloadExport(exportId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `export_${exportId}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Error downloading export:', err);
      alert('Failed to download export');
    }
  };

  const handleBulkDownload = async () => {
    if (selectedExports.length === 0) return;

    try {
      const blob = await api.downloadMultipleExports(selectedExports);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `bulk_export_${selectedExports.length}_files.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Error downloading exports:', err);
      alert('Failed to download exports');
    }
  };

  const toggleExportSelection = (exportId) => {
    setSelectedExports(prev =>
      prev.includes(exportId)
        ? prev.filter(id => id !== exportId)
        : [...prev, exportId]
    );
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'pending':
        return 'text-yellow-600 bg-yellow-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Export Management</h3>
        <div className="animate-pulse space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="border rounded-lg p-4">
              <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Export Management</h3>
        <div className="text-red-600 text-center py-4">{error}</div>
        <button
          onClick={loadExports}
          className="w-full bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Export Management</h3>
        {selectedExports.length > 0 && (
          <button
            onClick={handleBulkDownload}
            className="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600"
          >
            Download Selected ({selectedExports.length})
          </button>
        )}
      </div>

      <div className="space-y-4">
        {exports.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            No exports found
          </div>
        ) : (
          exports.map((exportItem) => (
            <div key={exportItem.id} className="border rounded-lg p-4 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={selectedExports.includes(exportItem.id)}
                    onChange={() => toggleExportSelection(exportItem.id)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-medium">{exportItem.job_name || 'Unknown Job'}</span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor('completed')}`}>
                        {exportItem.format.toUpperCase()}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      Created {formatDistanceToNow(new Date(exportItem.created_at), { addSuffix: true })}
                      {exportItem.file_size && (
                        <span className="ml-2">• {formatFileSize(exportItem.file_size)}</span>
                      )}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => handleDownload(exportItem.id)}
                  className="bg-green-500 text-white py-1 px-3 rounded text-sm hover:bg-green-600"
                >
                  Download
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ExportManagementPanel;