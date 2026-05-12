import React, { useMemo, useState } from 'react';
import { EmptyState } from './ui';

const MAX_COLUMNS = 10;
const focusClass = 'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950';

const asObjectRows = (results = []) => {
  if (!Array.isArray(results)) return [];

  const rows = [];

  results.forEach((entry, index) => {
    if (!entry) return;

    if (entry.data_json && typeof entry.data_json === 'object') {
      const payload = entry.data_json;
      if (Array.isArray(payload.items) && payload.items.length > 0) {
        payload.items.forEach((item, itemIndex) => {
          if (item && typeof item === 'object') {
            rows.push({
              __id: `${entry.id || index}-item-${itemIndex}`,
              __type: entry.data_type || 'record',
              ...item,
            });
          }
        });
        return;
      }

      rows.push({
        __id: String(entry.id || `result-${index}`),
        __type: entry.data_type || 'record',
        ...payload,
      });
      return;
    }

    if (typeof entry === 'object') {
      rows.push({
        __id: String(entry.id || `row-${index}`),
        __type: entry.data_type || 'record',
        ...entry,
      });
    }
  });

  return rows;
};

const stringify = (value) => {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

const compareValues = (left, right) => {
  const leftNumber = Number(left);
  const rightNumber = Number(right);
  if (Number.isFinite(leftNumber) && Number.isFinite(rightNumber)) {
    return leftNumber - rightNumber;
  }
  return String(left || '').localeCompare(String(right || ''), undefined, { sensitivity: 'base' });
};

const ResultsTable = ({ results = [] }) => {
  const [search, setSearch] = useState('');
  const [filterField, setFilterField] = useState('all');
  const [sortField, setSortField] = useState('');
  const [sortDirection, setSortDirection] = useState('asc');

  const rows = useMemo(() => asObjectRows(results), [results]);

  const columns = useMemo(() => {
    const set = new Set();
    rows.forEach((row) => {
      Object.keys(row)
        .filter((key) => !key.startsWith('__'))
        .forEach((key) => set.add(key));
    });
    return Array.from(set).slice(0, MAX_COLUMNS);
  }, [rows]);

  const filteredRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    const matchingRows = rows.filter((row) => {
      if (!normalizedSearch) return true;

      const sourceValues =
        filterField === 'all'
          ? Object.entries(row)
              .filter(([key]) => !key.startsWith('__'))
              .map(([, value]) => stringify(value))
          : [stringify(row[filterField])];

      return sourceValues.some((value) => value.toLowerCase().includes(normalizedSearch));
    });

    if (!sortField) {
      return matchingRows;
    }

    return [...matchingRows].sort((left, right) => {
      const delta = compareValues(left[sortField], right[sortField]);
      return sortDirection === 'asc' ? delta : -delta;
    });
  }, [rows, search, filterField, sortField, sortDirection]);

  if (rows.length === 0) {
    return (
      <EmptyState
        title="No records yet."
        description="Run a request to generate a results table."
      />
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-1">
          <label htmlFor="results-table-search" className="text-xs uppercase tracking-wide text-slate-400">
            Search
          </label>
          <input
            id="results-table-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search records"
            className={`w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 ${focusClass}`}
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="results-table-field" className="text-xs uppercase tracking-wide text-slate-400">
            Filter field
          </label>
          <select
            id="results-table-field"
            value={filterField}
            onChange={(event) => setFilterField(event.target.value)}
            className={`w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100 ${focusClass}`}
          >
            <option value="all">Search all fields</option>
            {columns.map((column) => (
              <option key={column} value={column}>
                {column}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label htmlFor="results-table-sort" className="text-xs uppercase tracking-wide text-slate-400">
            Sort by
          </label>
          <select
            id="results-table-sort"
            value={sortField}
            onChange={(event) => setSortField(event.target.value)}
            className={`w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100 ${focusClass}`}
          >
            <option value="">No sorting</option>
            {columns.map((column) => (
              <option key={column} value={column}>
                Sort by {column}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label htmlFor="results-table-direction" className="text-xs uppercase tracking-wide text-slate-400">
            Direction
          </label>
          <select
            id="results-table-direction"
            value={sortDirection}
            onChange={(event) => setSortDirection(event.target.value)}
            className={`w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100 ${focusClass}`}
          >
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-slate-950">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-white/10 text-sm">
            <thead className="bg-slate-900/60">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-slate-300">#</th>
                <th className="px-3 py-2 text-left font-medium text-slate-300">Type</th>
                {columns.map((column) => (
                  <th key={column} className="px-3 py-2 text-left font-medium text-slate-300">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredRows.map((row, index) => (
                <tr key={row.__id || index} className="hover:bg-slate-900/40">
                  <td className="px-3 py-2 text-slate-400">{index + 1}</td>
                  <td className="px-3 py-2 text-slate-300">{row.__type || 'record'}</td>
                  {columns.map((column) => (
                    <td key={`${row.__id}-${column}`} className="max-w-[320px] px-3 py-2 text-slate-200">
                      <span className="block truncate" title={stringify(row[column])}>
                        {stringify(row[column]) || '-'}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredRows.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">
            No rows matched your current search/filter settings.
          </p>
        )}
      </div>
    </div>
  );
};

export default ResultsTable;
