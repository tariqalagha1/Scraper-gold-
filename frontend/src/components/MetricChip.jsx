import React from 'react';

const MetricChip = ({ label, value }) => (
  <div className="inline-flex min-w-[132px] flex-col rounded-2xl border border-white/10 bg-surfaceAlt px-4 py-3 shadow-sm">
    <span className="text-[11px] uppercase tracking-[0.18em] text-textMuted">{label}</span>
    <span className="mt-2 text-sm font-medium text-textMain">{value}</span>
  </div>
);

export default MetricChip;
