import React from 'react';
import HistoryTable from '../components/HistoryTable';

const HistoryPage = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">History Management</h1>
          <p className="mt-2 text-gray-600">
            View and manage your scraping history, runs, and exports.
          </p>
        </div>

        <HistoryTable />
      </div>
    </div>
  );
};

export default HistoryPage;