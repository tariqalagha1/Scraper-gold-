import React from 'react';
import Card from './Card';

const EmptyState = ({ title = 'Nothing to show yet.', description = 'Once data is available, it will appear here.' }) => (
  <Card className="text-center">
    <p className="text-sm font-medium text-slate-200">{title}</p>
    <p className="mt-1 text-sm text-slate-400">{description}</p>
  </Card>
);

export default EmptyState;
