import React, { useState } from 'react';

const HistoryFilters = ({ onFiltersChange }) => {
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    itemType: '',
    status: '',
  });

  const handleFilterChange = (key, value) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const clearFilters = () => {
    const emptyFilters = {
      startDate: '',
      endDate: '',
      itemType: '',
      status: '',
    };
    setFilters(emptyFilters);
    onFiltersChange(emptyFilters);
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-surface p-4 mb-4 shadow-glow">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-textMuted mb-1">
            Start Date
          </label>
          <input
            type="date"
            value={filters.startDate}
            onChange={(e) => handleFilterChange('startDate', e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-bg/70 px-3 py-2 text-textMain focus:border-accent/40 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-textMuted mb-1">
            End Date
          </label>
          <input
            type="date"
            value={filters.endDate}
            onChange={(e) => handleFilterChange('endDate', e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-bg/70 px-3 py-2 text-textMain focus:border-accent/40 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-textMuted mb-1">
            Type
          </label>
          <select
            value={filters.itemType}
            onChange={(e) => handleFilterChange('itemType', e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-bg/70 px-3 py-2 text-textMain focus:border-accent/40 focus:outline-none"
          >
            <option value="">All Types</option>
            <option value="run">Runs</option>
            <option value="export">Exports</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-textMuted mb-1">
            Status
          </label>
          <select
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-bg/70 px-3 py-2 text-textMain focus:border-accent/40 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="running">Running</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
        </div>
      </div>
      <div className="mt-4 flex justify-end">
        <button
          onClick={clearFilters}
          className="px-4 py-2 text-sm text-textMuted transition hover:text-textMain"
        >
          Clear Filters
        </button>
      </div>
    </div>
  );
};

export default HistoryFilters;
