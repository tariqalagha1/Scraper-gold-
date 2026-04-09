import React, { useMemo, useState } from 'react';
import JsonPreview from './JsonPreview';
import StatusBadge from './StatusBadge';
import {
  formatConfidence,
  getMemoryTone,
  getRetryTone,
  getValidationTone,
} from '../utils/workflowContract';

const ResultPreview = ({ workflow, title = 'Extracted Data', description = 'Review the structured output and execution signals from the latest run.' }) => {
  const [showJson, setShowJson] = useState(false);
  const data = useMemo(
    () => (Array.isArray(workflow?.result?.data) ? workflow.result.data : []),
    [workflow]
  );
  const validation = workflow?.execution?.validation || {};
  const retry = workflow?.execution?.retry || {};
  const memory = workflow?.execution?.memory || {};
  const decision = workflow?.execution?.decision || {};

  const summary = useMemo(() => {
    const count = data.length;
    if (count > 0) {
      return `${count} item${count === 1 ? '' : 's'} extracted`;
    }
    if ((workflow?.status || '').toLowerCase() === 'failed') {
      return 'No structured data returned';
    }
    return 'Waiting for structured data';
  }, [data, workflow?.status]);

  return (
    <div className="rounded-2xl border border-white/10 bg-surface p-6 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-textMuted">Result Preview</p>
          <h3 className="mt-2 text-lg font-semibold text-textMain">{title}</h3>
          <p className="mt-3 text-sm leading-6 text-textMuted">{description}</p>
        </div>
        <button
          type="button"
          onClick={() => setShowJson((previous) => !previous)}
          className="rounded-full border border-white/10 px-4 py-2 text-sm text-textMuted transition hover:border-accent/30 hover:text-textMain"
        >
          {showJson ? 'Show Cards' : 'Show JSON'}
        </button>
      </div>

      <div className="mt-5 rounded-xl border border-white/10 bg-bg/70 p-4">
        <div className="flex flex-wrap gap-3">
          <StatusBadge status={getValidationTone(validation.status)}>
            validation {validation.status || 'unknown'}
          </StatusBadge>
          <StatusBadge status={getRetryTone(retry)}>
            retry {retry.attempted ? 'attempted' : 'not needed'}
          </StatusBadge>
          <StatusBadge status={getMemoryTone(memory)}>
            {memory.used ? 'memory active' : 'first run'}
          </StatusBadge>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-textMuted">Summary</p>
            <p className="mt-2 text-sm text-textMain">{summary}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-textMuted">Page Understanding</p>
            <p className="mt-2 text-sm text-textMain">
              {decision.page_type || 'unknown'} · {formatConfidence(decision.confidence)}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-6">
        {showJson ? (
          <JsonPreview data={data.slice(0, 5)} />
        ) : (
          <div className="space-y-3">
            {data.slice(0, 5).map((item, index) => (
              <div key={`${item.link || item.title || item.name || index}`} className="rounded-2xl border border-white/10 bg-bg/60 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-textMuted">Record {index + 1}</p>
                    <h4 className="mt-2 text-sm font-semibold text-textMain">
                      {item.title || item.name || item.label || `Item ${index + 1}`}
                    </h4>
                    <p className="mt-2 text-sm text-textMuted">
                      {item.link || item.url || item.source_url || 'No source link'}
                    </p>
                  </div>
                  {(item.price || item.amount || item.value) && (
                    <span className="rounded-full border border-accent/30 bg-accentSoft px-3 py-1 text-xs text-accent">
                      {item.price || item.amount || item.value}
                    </span>
                  )}
                </div>
              </div>
            ))}

            {data.length === 0 && (
              <div className="rounded-2xl border border-white/10 bg-bg/60 p-5 text-sm text-textMuted">
                No structured records are available yet.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultPreview;
