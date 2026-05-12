import React, { useMemo, useState } from 'react';
import InsightsPanel from './InsightsPanel';
import ResultsTable from './ResultsTable';
import { Section } from './ui';

const focusClass = 'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950';

const fallbackInsights = (result) => {
  const total = Number(result?.total || 0);
  const sourceCount = Array.isArray(result?.sources) ? result.sources.length : 0;
  const confidence = Number(result?.quality?.confidence || 0);
  const coverage = Number(result?.quality?.coverage || 0);

  return {
    summary:
      total > 0
        ? `We found ${total} records from ${sourceCount} source${sourceCount === 1 ? '' : 's'}.`
        : 'No records were found for this request yet.',
    key_findings: [
      `Confidence is around ${Math.round(confidence * 100)}%.`,
      `Coverage is around ${Math.round(coverage * 100)}%.`,
    ],
    data_quality_note:
      coverage >= 0.75 && confidence >= 0.75
        ? 'Data quality looks strong for immediate review.'
        : 'Some fields are incomplete, so review records before sharing.',
    recommended_next_step:
      total === 0
        ? 'Try a broader query or remove strict filters, then run again.'
        : 'Export results and share with your team, then run a focused follow-up if needed.',
  };
};

const labelForConfidence = (value) => {
  if (value >= 0.85) return 'High confidence';
  if (value >= 0.6) return 'Moderate confidence';
  return 'Low confidence';
};

const labelForCoverage = (value) => {
  if (value >= 0.85) return 'Strong coverage';
  if (value >= 0.6) return 'Partial coverage';
  return 'Limited coverage';
};

const ResultsPage = ({ result, onCopy, onExport, onRerun }) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const insights = useMemo(() => {
    if (
      result?.insights
      && typeof result.insights.summary === 'string'
      && Array.isArray(result.insights.key_findings)
    ) {
      return result.insights;
    }
    return fallbackInsights(result);
  }, [result]);

  const sourceCount = Array.isArray(result?.sources) ? result.sources.length : 0;
  const totalRecords = Number(result?.total || result?.data?.length || 0);
  const confidence = Number(result?.quality?.confidence || 0);
  const coverage = Number(result?.quality?.coverage || 0);
  const warnings = Array.isArray(result?.errors) ? result.errors : [];

  const normalizedMissing = Object.entries(result?.quality?.missing_fields || {})
    .map(([field, count]) => ({ field, count: Number(count) || 0 }))
    .filter((entry) => entry.count > 0)
    .sort((left, right) => right.count - left.count);

  if (!result) {
    return null;
  }

  return (
    <section className="space-y-4">
      <Section
        title="Results summary"
        description={insights.summary}
        action={
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
            <button
              type="button"
              onClick={onExport}
              className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 transition hover:border-slate-500 sm:w-auto ${focusClass}`}
            >
              Export
            </button>
            <button
              type="button"
              onClick={onCopy}
              className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 transition hover:border-slate-500 sm:w-auto ${focusClass}`}
            >
              Copy
            </button>
            <button
              type="button"
              onClick={onRerun}
              className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 transition hover:border-slate-500 sm:w-auto ${focusClass}`}
            >
              Re-run
            </button>
          </div>
        }
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-white/10 bg-slate-900 p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Records</p>
            <p className="mt-1 text-xl font-semibold text-slate-100">{totalRecords}</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-slate-900 p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Sources</p>
            <p className="mt-1 text-xl font-semibold text-slate-100">{sourceCount}</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-slate-900 p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Quality</p>
            <p className="mt-1 text-xl font-semibold text-slate-100">{labelForConfidence(confidence)}</p>
            <p className="text-xs text-slate-400">about {Math.round(confidence * 100)}% confidence</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-slate-900 p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Coverage</p>
            <p className="mt-1 text-xl font-semibold text-slate-100">{labelForCoverage(coverage)}</p>
            <p className="text-xs text-slate-400">about {Math.round(coverage * 100)}% of requested fields</p>
          </div>
        </div>
      </Section>

      <InsightsPanel
        data={result.data || []}
        sources={result.sources || []}
        quality={result.quality || {}}
        missingFields={result.missing_fields || result.quality?.missing_fields || {}}
        total={totalRecords}
      />

      <Section title="Records" description="Search, sort, and filter the extracted table.">
        <ResultsTable results={result.data || []} />
      </Section>

      <Section title="Missing data" description="A plain-language explanation of the most important gaps.">
        {normalizedMissing.length === 0 ? (
          <p className="text-sm text-slate-300">No critical missing fields were reported.</p>
        ) : (
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
            {normalizedMissing.slice(0, 4).map((entry) => (
              <li key={entry.field}>
                {entry.field} is missing in {entry.count} record{entry.count === 1 ? '' : 's'}.
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Next actions" description="Suggested follow-up steps based on the current run.">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>{insights.recommended_next_step || 'Export this run and validate critical records.'}</li>
          <li>{confidence < 0.7 ? 'Validate a sample manually before sharing externally.' : 'Share with your team and monitor exceptions.'}</li>
          <li>{coverage < 0.7 ? 'Run again with broader sources to improve field coverage.' : 'Use this output for downstream analysis or outreach.'}</li>
        </ul>
      </Section>

      {(warnings.length > 0 || showAdvanced) && (
        <Section title="Advanced" description="Technical details and debug payloads are hidden by default.">
          <button
            type="button"
            onClick={() => setShowAdvanced((value) => !value)}
            className={`text-sm font-medium text-slate-200 ${focusClass}`}
            aria-expanded={showAdvanced}
            aria-controls="results-advanced-content"
          >
            {showAdvanced ? 'Hide' : 'Show'} Advanced
          </button>

          {warnings.length > 0 && (
            <div className="mt-3 rounded-xl border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-sm text-amber-200" role="alert">
              <p className="font-medium">Errors and warnings</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {warnings.map((warning, index) => (
                  <li key={`${warning}-${index}`}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          {showAdvanced && (
            <pre id="results-advanced-content" className="mt-3 max-h-80 overflow-auto rounded-xl border border-white/10 bg-slate-900 p-3 text-xs text-slate-300">
              {JSON.stringify(result.raw || result, null, 2)}
            </pre>
          )}
        </Section>
      )}
    </section>
  );
};

export default ResultsPage;
