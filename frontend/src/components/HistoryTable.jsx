import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import HistoryFilters from './HistoryFilters';
import api from '../services/api';

const HistoryTable = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({});
  const [error, setError] = useState('');

  useEffect(() => {
    fetchHistory();
  }, [filters]);

  const mapFiltersToApiParams = (activeFilters) => ({
    start_date: activeFilters.startDate || undefined,
    end_date: activeFilters.endDate || undefined,
    item_type: activeFilters.itemType || undefined,
    status: activeFilters.status || undefined,
  });

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const data = await api.getUserHistory(mapFiltersToApiParams(filters));
      setHistory(data.items || []);
      setError('');
    } catch (error) {
      console.error('Error fetching history:', error);
      setError(error?.response?.data?.detail || 'Could not load history right now.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (itemId, itemType) => {
    if (!window.confirm('Are you sure you want to delete this item?')) return;

    try {
      await api.deleteHistoryItem(itemId, itemType);
      await fetchHistory();
    } catch (error) {
      console.error('Error deleting item:', error);
      setError(error?.response?.data?.detail || 'Could not delete this history item.');
    }
  };

  if (loading) {
    return <div className="p-4 text-textMuted">Loading history...</div>;
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-surface shadow-glow">
      <div className="p-6">
        <h3 className="text-lg font-semibold mb-4 text-textMain">History</h3>
        {error && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </div>
        )}
        <HistoryFilters onFiltersChange={setFilters} />
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-white/10">
            <thead className="bg-bg/70">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-textMuted uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-textMuted uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-textMuted uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-textMuted uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-textMuted uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-surface divide-y divide-white/10">
              {history.map((item) => (
                <tr key={item.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-textMain capitalize">
                    {item.type}
                  </td>
                  <td className="px-6 py-4 text-sm text-textMain">
                    {item.title}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      item.status === 'completed' ? 'bg-green-100 text-green-800' :
                      item.status === 'running' ? 'bg-blue-100 text-blue-800' :
                      item.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {item.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-textMuted">
                    {format(new Date(item.timestamp), 'MMM dd, yyyy HH:mm')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => handleDelete(item.id, item.type)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {history.length === 0 && (
            <p className="text-textMuted text-center py-8">No history items found</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryTable;
