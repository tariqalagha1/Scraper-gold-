import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import HistoryFilters from './HistoryFilters';

const HistoryTable = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({});

  useEffect(() => {
    fetchHistory();
  }, [filters]);

  const fetchHistory = async () => {
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });

      const response = await fetch(`/api/v1/user/history?${params}`);
      const data = await response.json();
      setHistory(data.items || []);
    } catch (error) {
      console.error('Error fetching history:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (itemId, itemType) => {
    if (!confirm('Are you sure you want to delete this item?')) return;

    try {
      await fetch(`/api/v1/user/history/${itemId}?item_type=${itemType}`, {
        method: 'DELETE',
      });
      fetchHistory(); // Refresh
    } catch (error) {
      console.error('Error deleting item:', error);
    }
  };

  if (loading) {
    return <div className="p-4">Loading history...</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6">
        <h3 className="text-lg font-semibold mb-4">History</h3>
        <HistoryFilters onFiltersChange={setFilters} />
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
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
              {history.map((item) => (
                <tr key={item.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 capitalize">
                    {item.type}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
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
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
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
            <p className="text-gray-500 text-center py-8">No history items found</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryTable;