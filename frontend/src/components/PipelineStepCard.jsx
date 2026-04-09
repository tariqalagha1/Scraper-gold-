import React from 'react';
import StatusBadge from './StatusBadge';

const PipelineStepCard = ({ title, status, description, detail, metrics = [] }) => (
  <div className="rounded-[28px] border border-white/10 bg-surfaceAlt p-6 shadow-sm">
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="inline-flex rounded-full border border-white/10 bg-bg/80 px-3 py-1">
          <p className="text-[11px] uppercase tracking-[0.24em] text-textMuted">{title}</p>
        </div>
        <h3 className="mt-4 text-xl font-semibold text-textMain">{description}</h3>
      </div>
      <StatusBadge status={status} />
    </div>

    {(detail || metrics.length > 0) && (
      <div className="mt-5 space-y-4">
        {detail && <p className="text-sm leading-7 text-textMuted">{detail}</p>}
        {metrics.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2">
            {metrics.map((item) => (
              <div key={`${title}-${item.label}`} className="rounded-2xl border border-white/10 bg-bg/80 px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-textMuted">{item.label}</p>
                <p className="mt-2 text-sm font-medium text-textMain">{item.value}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    )}
  </div>
);

export default PipelineStepCard;
