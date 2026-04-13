import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';

const ExportStatusView = () => {
  const [exports, setExports] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExports();
    fetchStats();
  }, []);

  const fetchExports = async () => {
    try {
      const response = await fetch('/api/v1/exports');
      const data = await response.json();
      setExports(data.exports || []);
    } catch (error) {
      console.error('Error fetching exports:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/v1/exports/stats');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (exportId) => {
    window.open(`/api/v1/exports/${exportId}/download`, '_blank');
  };

  if (loading) {
    return <div className="p-4">Loading exports...</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Export Management</h3>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-blue-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-blue-600">{stats.total_exports || 0}</div>
          <div className="text-sm text-blue-800">Total Exports</div>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-green-600">
            {(stats.total_size_bytes / (1024 * 1024)).toFixed(1)} MB
          </div>
          <div className="text-sm text-green-800">Total Size</div>
        </div>
        <div className="bg-purple-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-purple-600">{Object.keys(stats.formats || {}).length}</div>
          <div className="text-sm text-purple-800">Formats</div>
        </div>
      </div>

      {/* Export List */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Job
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Format
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Size
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {exports.map((export_) => (
              <tr key={export_.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {export_.job_name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 capitalize">
                  {export_.format}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {(export_.file_size / 1024).toFixed(1)} KB
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {format(new Date(export_.created_at), 'MMM dd, yyyy')}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => handleDownload(export_.id)}
                    className="text-blue-600 hover:text-blue-900"
                  >
                    Download
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {exports.length === 0 && (
          <p className="text-gray-500 text-center py-8">No exports found</p>
        )}
      </div>
    </div>
  );
};

export default ExportStatusView;