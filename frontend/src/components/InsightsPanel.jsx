import React, { useMemo, useState } from 'react';
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  LineChart,
  SearchCheck,
  ShieldCheck,
} from 'lucide-react';

const MAX_BULLETS = 4;

const clampRatio = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(1, numeric));
};

const toPercent = (value) => Math.round(clampRatio(value) * 100);
const humanizedPercent = (value) => `around ${toPercent(value)}%`;

const ensureRows = (value) => (Array.isArray(value) ? value.filter((row) => row && typeof row === 'object') : []);

const ensureSources = (value) =>
  (Array.isArray(value) ? value : [])
    .map((item) => {
      const name = String(item?.name || '').trim();
      const count = Number(item?.count);
      if (!name) return null;
      return { name, count: Number.isFinite(count) && count >= 0 ? Math.floor(count) : 0 };
    })
    .filter(Boolean);

const ensureMissingFields = (value) => {
  if (!value || typeof value !== 'object') return [];
  return Object.entries(value)
    .map(([field, count]) => ({ field: String(field), count: Number(count) || 0 }))
    .filter((entry) => entry.field.trim())
    .sort((left, right) => right.count - left.count);
};

const findSimplePatterns = (rows) => {
  if (!Array.isArray(rows) || rows.length === 0) return [];

  const counters = {};
  rows.forEach((row) => {
    Object.entries(row)
      .slice(0, 12)
      .forEach(([field, raw]) => {
        if (raw === null || raw === undefined) return;
        if (typeof raw === 'object') return;

        const value = String(raw).trim();
        if (!value || value.length > 60) return;
        const key = `${field}::${value.toLowerCase()}`;
        if (!counters[key]) {
          counters[key] = { field, value, count: 0 };
        }
        counters[key].count += 1;
      });
  });

  return Object.values(counters)
    .filter((entry) => entry.count >= 2)
    .sort((left, right) => right.count - left.count)
    .slice(0, MAX_BULLETS);
};

const buildInsightsSections = ({ data, sources, quality, missingFields, total }) => {
  const rows = ensureRows(data);
  const normalizedSources = ensureSources(sources);
  const safeTotal = Math.max(0, Number(total) || rows.length || 0);
  const coverage = clampRatio(quality?.coverage);
  const confidence = clampRatio(quality?.confidence);
  const duplicatesRemoved = Math.max(0, Number(quality?.duplicates_removed || 0));
  const normalizedMissing = ensureMissingFields(missingFields);
  const topMissing = normalizedMissing[0] || null;
  const topSource = [...normalizedSources].sort((left, right) => right.count - left.count)[0] || null;
  const simplePatterns = findSimplePatterns(rows);
  const topSourceShare = topSource && safeTotal > 0 ? Math.round((topSource.count / safeTotal) * 100) : 0;

  const keyFindings = [
    `Collected ${safeTotal} result${safeTotal === 1 ? '' : 's'} from ${normalizedSources.length} source${normalizedSources.length === 1 ? '' : 's'}.`,
    `Coverage is ${humanizedPercent(coverage)} and confidence is ${humanizedPercent(confidence)}.`,
    topSource ? `${topSource.name} contributed the largest share (${topSource.count} records).` : 'Source breakdown is limited in this run.',
    duplicatesRemoved > 0 ? `${duplicatesRemoved} duplicate record${duplicatesRemoved === 1 ? '' : 's'} were removed.` : 'No duplicate cleanup was needed.',
  ].slice(0, MAX_BULLETS);

  const dataQuality = [
    coverage >= 0.8 ? 'Most requested information is present.' : 'Some requested information is still missing.',
    confidence >= 0.8 ? 'Confidence is strong for decision support.' : 'Confidence is moderate; validate critical rows before sharing.',
    normalizedMissing.length > 0
      ? `${normalizedMissing.length} field${normalizedMissing.length === 1 ? '' : 's'} have visible gaps.`
      : 'No major field gaps were reported.',
    safeTotal > 0 ? `Average confidence per record is ${humanizedPercent(confidence)}.` : 'Quality metrics are limited because no records were returned.',
  ].slice(0, MAX_BULLETS);

  const observations = [
    ...simplePatterns.map(
      (entry) => `"${entry.value}" appears often in ${entry.field} (${entry.count} records).`
    ),
    topSource && topSourceShare >= 70
      ? `${topSource.name} dominates this run (${topSourceShare}% of all records).`
      : normalizedSources.length > 1
        ? 'Results are spread across multiple sources.'
        : 'Only one source appears in this run.',
    safeTotal > 0 && rows.length > 0 ? `The run produced ${rows.length} structured rows for review.` : 'No stable row pattern is available yet.',
  ]
    .filter(Boolean)
    .slice(0, MAX_BULLETS);

  const dataGaps = [
    safeTotal === 0 ? 'No records were returned for this request.' : '',
    topMissing
      ? `${topMissing.field} is missing in ${topMissing.count} record${topMissing.count === 1 ? '' : 's'}${safeTotal > 0 ? ` (${humanizedPercent(topMissing.count / safeTotal)})` : ''}.`
      : 'No critical missing field was identified.',
    ...normalizedMissing
      .slice(1, 3)
      .map((entry) => `${entry.field} is missing in ${entry.count} record${entry.count === 1 ? '' : 's'}.`),
  ]
    .filter(Boolean)
    .slice(0, MAX_BULLETS);

  const suggestedActions = [
    safeTotal === 0
      ? 'Broaden your query or remove strict constraints, then run again.'
      : 'Export this result set and review high-value rows first.',
    topMissing ? `Run a follow-up focused on improving ${topMissing.field} completeness.` : 'Run a targeted follow-up for any business-critical field.',
    topSource && topSourceShare >= 70 ? `Add alternate sources to reduce dependence on ${topSource.name}.` : 'Keep current source mix and monitor consistency over the next run.',
    confidence < 0.7 ? 'Manually verify a sample before sharing externally.' : 'Proceed with stakeholder sharing and track exceptions.',
  ].slice(0, MAX_BULLETS);

  return {
    keyFindings,
    dataQuality,
    observations,
    dataGaps,
    suggestedActions,
  };
};

const Section = ({ icon: Icon, title, bullets }) => (
  <div className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
    <div className="flex items-center gap-2">
      <Icon size={15} className="text-slate-300" />
      <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
    </div>
    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-300">
      {bullets.slice(0, MAX_BULLETS).map((item, index) => (
        <li key={`${title}-${index}`}>{item}</li>
      ))}
    </ul>
  </div>
);

const InsightsPanel = ({ data = [], sources = [], quality = {}, missingFields = {}, total = 0 }) => {
  const [collapsed, setCollapsed] = useState(false);

  const hasData = Math.max(0, Number(total) || 0) > 0 || ensureRows(data).length > 0;

  const sections = useMemo(
    () => buildInsightsSections({ data, sources, quality, missingFields, total }),
    [data, sources, quality, missingFields, total]
  );

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-slate-100">Insights</h2>
          <p className="mt-1 text-sm text-slate-400">
            Human-readable takeaways generated from your current result set.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setCollapsed((value) => !value)}
          className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-slate-900 px-2 py-1 text-xs text-slate-300 transition hover:border-slate-500 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950"
          aria-expanded={!collapsed}
          aria-controls="insights-panel-content"
        >
          {collapsed ? (
            <>
              Expand <ChevronDown size={14} />
            </>
          ) : (
            <>
              Collapse <ChevronUp size={14} />
            </>
          )}
        </button>
      </div>

      {!collapsed && (
        <div id="insights-panel-content">
          {!hasData ? (
            <p className="mt-3 rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-300">
              No insights available yet.
            </p>
          ) : (
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              <Section icon={SearchCheck} title="Key Findings" bullets={sections.keyFindings} />
              <Section icon={ShieldCheck} title="Data Quality" bullets={sections.dataQuality} />
              <Section icon={LineChart} title="Observations" bullets={sections.observations} />
              <Section icon={AlertTriangle} title="Data Gaps" bullets={sections.dataGaps} />
              <div className="lg:col-span-2">
                <Section icon={Lightbulb} title="Suggested Actions" bullets={sections.suggestedActions} />
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
};

export default InsightsPanel;
