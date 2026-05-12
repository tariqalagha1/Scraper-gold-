import React from 'react';
import HistoryList from '../components/HistoryList';
import { PageHeader } from '../components/ui';

const HistoryPage = () => {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Run History"
        description="Track previous runs and use quick actions to continue work."
      />
      <HistoryList />
    </div>
  );
};

export default HistoryPage;
