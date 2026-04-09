import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import MetricChip from '../components/MetricChip';
import PipelineStepCard from '../components/PipelineStepCard';
import ResultPreview from '../components/ResultPreview';
import SectionHeader from '../components/SectionHeader';
import StatusBadge from '../components/StatusBadge';
import api from '../services/api';
import { formatDate, getErrorMessage } from '../utils/helpers';
import {
  buildWorkflowContract,
  formatConfidence,
  formatDurationMs,
  getMemoryTone,
  getRetryTone,
  getValidationTone,
} from '../utils/workflowContract';

const POLL_INTERVAL_MS = 4000;

const normalizeStepStatus = (status, successState = 'success') => {
  const normalized = String(status || '').toLowerCase();
  if (!normalized || normalized === 'idle') {
    return 'pending';
  }
  if (normalized === 'failed') {
    return 'fail';
  }
  if (normalized === 'completed') {
    return successState;
  }
  if (normalized === 'running') {
    return 'running';
  }
  return 'pending';
};

const humanizeRunActionError = (requestError, fallback) => {
  const detail = requestError?.response?.data?.detail;
  const parsedMessage = getErrorMessage(requestError, fallback);
  const statusCode = requestError?.response?.status;
  const normalized = String(detail || parsedMessage || '').toLowerCase();
  if (typeof detail === 'string' && detail.toLowerCase().includes('missing api key')) {
    return 'Your backend is still enforcing API-key mode for this action. Restart backend and refresh this page.';
  }
  if (normalized.includes('plan job limit reached') || normalized.includes('plan daily run limit reached')) {
    return 'Your account is on the Free plan and hit its limit. API provider keys are separate and do not upgrade plan limits.';
  }
  if (statusCode === 429) {
    return 'Too many requests were sent in a short window. Please wait a few seconds and try again.';
  }
  return parsedMessage || fallback;
};

const humanizeLoadError = (requestError) => {
  const parsedMessage = getErrorMessage(requestError, 'Could not load the execution trace.');
  const statusCode = requestError?.response?.status;
  if (statusCode === 429) {
    return 'Live updates are temporarily rate-limited. Please wait a few seconds.';
  }
  return parsedMessage;
};

const formatJobTitle = (rawUrl) => {
  const value = String(rawUrl || '').trim();
  if (!value) {
    return 'Job workspace';
  }

  try {
    const parsed = new URL(value);
    const normalizedPath = parsed.pathname && parsed.pathname !== '/' ? parsed.pathname : '';
    const core = `${parsed.hostname}${normalizedPath}`;
    return core.length > 84 ? `${core.slice(0, 81)}...` : core;
  } catch {
    return value.length > 84 ? `${value.slice(0, 81)}...` : value;
  }
};

const graphToneClasses = {
  success: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200',
  running: 'border-accent/40 bg-accentSoft text-accent',
  pending: 'border-white/10 bg-bg/70 text-textMuted',
  fail: 'border-danger/30 bg-danger/10 text-danger',
};

const JobDetailPage = () => {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [runs, setRuns] = useState([]);
  const [results, setResults] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [startingRun, setStartingRun] = useState(false);
  const [retryingRun, setRetryingRun] = useState(false);
  const [error, setError] = useState('');

  const latestRun = runs[0] || null;
  const workflow = useMemo(
    () =>
      buildWorkflowContract({
        job,
        run: latestRun,
        results,
        logs,
      }),
    [job, latestRun, results, logs]
  );
  const hasActiveRun = ['pending', 'running'].includes(workflow.status);
  const data = useMemo(
    () => (Array.isArray(workflow.result?.data) ? workflow.result.data : []),
    [workflow]
  );
  const decision = useMemo(() => workflow.execution?.decision || {}, [workflow]);
  const validation = useMemo(() => workflow.execution?.validation || {}, [workflow]);
  const retry = useMemo(() => workflow.execution?.retry || {}, [workflow]);
  const memory = useMemo(() => workflow.execution?.memory || {}, [workflow]);
  const metadata = useMemo(() => workflow.metadata || {}, [workflow]);
  const progress = workflow.execution?.steps?.progress ?? 0;
  const extractedItemSummary =
    data.length > 0
      ? `${data.length} items extracted`
      : workflow.status === 'failed'
        ? 'No structured records available'
        : 'Extraction results will appear here';
  const waitGraphSteps = useMemo(() => {
    const completedOrActive = ['pending', 'running', 'completed', 'failed'].includes(workflow.status);
    const decisionReady = decision.page_type && decision.page_type !== 'unknown';
    const validationReady = Boolean(validation.status);

    return [
      {
        title: 'Inspect',
        caption: decisionReady ? decision.page_type : 'Page check',
        status: decisionReady ? 'success' : completedOrActive ? normalizeStepStatus(workflow.status) : 'pending',
      },
      {
        title: 'Capture',
        caption: hasActiveRun ? `${progress}% live` : workflow.status === 'completed' ? `${progress}% done` : 'Browser work',
        status: normalizeStepStatus(workflow.status),
      },
      {
        title: 'Shape',
        caption: data.length > 0 ? `${data.length} records` : 'Structuring',
        status: data.length > 0 ? 'success' : normalizeStepStatus(workflow.status),
      },
      {
        title: 'Check',
        caption: validation.status || 'Quality gate',
        status: validationReady ? getValidationTone(validation.status) : workflow.status === 'completed' ? 'success' : normalizeStepStatus(workflow.status),
      },
      {
        title: 'Deliver',
        caption: workflow.status === 'completed' ? 'Result ready' : 'Packaging',
        status: workflow.status === 'completed' ? 'success' : workflow.status === 'failed' ? 'fail' : 'pending',
      },
    ];
  }, [data.length, decision.page_type, hasActiveRun, progress, validation.status, workflow.status]);
  const codeActions = useMemo(() => {
    const baseActions = [
      'open_page(url)',
      'detect_layout()',
      'extract_records()',
      'validate_output()',
      'package_exports()',
    ];

    let activeIndex = 0;
    if (workflow.status === 'completed') {
      activeIndex = baseActions.length - 1;
    } else if (workflow.status === 'failed') {
      activeIndex = Math.min(3, baseActions.length - 1);
    } else if (progress >= 75) {
      activeIndex = 3;
    } else if (progress >= 45) {
      activeIndex = 2;
    } else if (progress >= 20) {
      activeIndex = 1;
    }

    return baseActions.map((action, index) => ({
      action,
      state:
        workflow.status === 'failed' && index > activeIndex
          ? 'pending'
          : index < activeIndex || workflow.status === 'completed'
            ? 'done'
            : index === activeIndex
              ? workflow.status === 'completed'
                ? 'done'
                : 'active'
              : 'pending',
    }));
  }, [progress, workflow.status]);
  const waitBoxMessage = hasActiveRun
    ? 'The worker is still moving through browser, extraction, and validation work. A progress pause usually means the page is rendering or being checked, not that the run is stuck.'
    : workflow.status === 'completed'
      ? 'This is the same path the worker just finished. Users can see how the result was assembled, not just the final output.'
      : workflow.status === 'failed'
        ? 'The run stopped before delivery, but the graph still shows where the worker spent time so the user understands what happened.'
        : 'When a run starts, this box turns into a live behind-the-scenes view of how the worker moves from page inspection to final delivery.';

  const loadJobData = useCallback(
    async ({ silent = false } = {}) => {
      if (!id) {
        return;
      }

      if (!silent) {
        setLoading(true);
      }

      try {
        const [jobData, runsData] = await Promise.all([api.getJob(id), api.getRunsByJob(id)]);
        setJob(jobData);
        setRuns(runsData);

        const targetRun = runsData[0] || null;
        if (targetRun) {
          const [resultsData, runLogs] = await Promise.all([
            api.getResults(targetRun.id),
            api.getRunLogs(targetRun.id),
          ]);
          setResults(resultsData);
          setLogs(runLogs);
        } else {
          setResults([]);
          setLogs([]);
        }
        setError('');
      } catch (requestError) {
        setError(humanizeLoadError(requestError));
      } finally {
        if (!silent) {
          setLoading(false);
        }
      }
    },
    [id]
  );

  useEffect(() => {
    loadJobData();
  }, [loadJobData]);

  useEffect(() => {
    if (!latestRun || !['pending', 'running'].includes(latestRun.status)) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      loadJobData({ silent: true });
    }, POLL_INTERVAL_MS);

    return () => window.clearTimeout(timer);
  }, [latestRun, loadJobData]);

  const handleStartRun = async () => {
    if (!id) {
      return;
    }

    try {
      setStartingRun(true);
      setError('');
      await api.startJobRun(id);
      await loadJobData({ silent: true });
    } catch (requestError) {
      setError(humanizeRunActionError(requestError, 'Could not start a new run.'));
    } finally {
      setStartingRun(false);
    }
  };

  const handleRetryRun = async () => {
    if (!latestRun) {
      return;
    }

    try {
      setRetryingRun(true);
      setError('');
      await api.retryRun(latestRun.id);
      await loadJobData({ silent: true });
    } catch (requestError) {
      setError(humanizeRunActionError(requestError, 'Could not retry this run.'));
    } finally {
      setRetryingRun(false);
    }
  };

  const timelineSteps = useMemo(() => {
    return [
      {
        title: 'Decision',
        status: decision.page_type && decision.page_type !== 'unknown' ? 'success' : normalizeStepStatus(workflow.status),
        description: decision.page_type && decision.page_type !== 'unknown' ? 'AI page understanding completed' : 'Decision details are still loading',
        detail: decision.reason || 'The system classified the page before extraction started.',
        metrics: [
          { label: 'Page Type', value: decision.page_type || 'unknown' },
          { label: 'Confidence', value: formatConfidence(decision.confidence) },
        ],
      },
      {
        title: 'Extraction',
        status: normalizeStepStatus(workflow.status),
        description:
          workflow.status === 'failed'
            ? 'Extraction ended before a complete output was produced'
            : workflow.status === 'completed'
              ? 'Structured extraction completed'
              : 'The extraction engine is still running',
        detail: 'The engine used the selected extraction strategy to gather user-facing records.',
        metrics: [
          { label: 'Data Count', value: `${data.length}` },
          { label: 'Progress', value: `${progress}%` },
        ],
      },
      {
        title: 'Validation',
        status: getValidationTone(validation.status),
        description:
          validation.status === 'pass'
            ? 'Validation passed and the output was accepted'
            : validation.status === 'fail'
              ? 'Validation could not confirm a clean result'
              : 'Validation will score output quality when extraction finishes',
        detail: 'Quality checks run after extraction to confirm the output is usable.',
        metrics: [
          { label: 'Result', value: validation.status || 'unknown' },
          { label: 'Confidence', value: formatConfidence(validation.confidence) },
        ],
      },
      {
        title: 'Retry',
        status: getRetryTone(retry),
        description: retry.attempted
          ? 'A recovery retry was triggered for this run history'
          : workflow.status === 'failed'
            ? 'Retry is available because the last run failed'
            : 'Retry was not needed for this run',
        detail: 'The retry engine only activates when the system detects a recoverable failure.',
        metrics: [
          { label: 'Attempted', value: retry.attempted ? 'Yes' : 'No' },
          { label: 'Result', value: retry.attempted ? (retry.result ? 'Recovered' : 'Still failed') : 'Skipped' },
        ],
      },
      {
        title: 'Memory',
        status: getMemoryTone(memory),
        description: memory.used ? 'Using learned extraction pattern' : 'First time seeing this domain',
        detail: memory.used
          ? 'The backend reused a learned extraction pattern for this run.'
          : 'No learned pattern was applied to this run snapshot.',
        metrics: [
          { label: 'Memory Used', value: memory.used ? 'Yes' : 'No' },
          { label: 'Selector Source', value: memory.selector_source || 'generated' },
        ],
      },
    ];
  }, [decision, workflow, data.length, validation, retry, memory, progress]);

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-10 lg:px-8">
        <div className="rounded-[28px] border border-white/10 bg-surface p-10 text-center text-textMuted shadow-glow">
          Loading execution trace...
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-10 lg:px-8">
        <div className="rounded-[28px] border border-danger/20 bg-danger/10 p-10 text-center text-danger">
          Job not found.
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 lg:px-8">
      <SectionHeader
        eyebrow="Execution Trace"
        title={formatJobTitle(workflow.request?.url || job.url)}
        description="This page shows the live execution path for the current job: decision, extraction, validation, retry, memory, and structured output."
      />

      <div className="mt-8 flex flex-wrap items-center gap-3">
        <StatusBadge status={workflow.status === 'completed' ? 'success' : workflow.status === 'failed' ? 'fail' : workflow.status || 'pending'}>
          {workflow.status || 'no run'}
        </StatusBadge>
        <MetricChip label="Scrape Type" value={workflow.request?.scrape_type || job.scrape_type} />
        <MetricChip label="Progress" value={`${progress}%`} />
        <MetricChip label="Run ID" value={metadata.run_id || 'Pending'} />
        <MetricChip label="Duration" value={formatDurationMs(metadata.duration_ms)} />
        <MetricChip label="Started" value={formatDate(metadata.started_at)} />
        <MetricChip label="Finished" value={formatDate(metadata.finished_at)} />
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={handleStartRun}
          disabled={startingRun || hasActiveRun}
          className="rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-bg transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {hasActiveRun ? 'Run in progress...' : startingRun ? 'Starting...' : 'Start Run'}
        </button>
        {latestRun && (
          <button
            type="button"
            onClick={handleRetryRun}
            disabled={retryingRun}
            className="rounded-2xl border border-white/10 px-5 py-3 text-sm text-textMuted transition hover:border-accent/30 hover:text-textMain disabled:cursor-not-allowed disabled:opacity-60"
          >
            {retryingRun ? 'Retrying...' : 'Retry Run'}
          </button>
        )}
      </div>

      {error && (
        <div className="mt-6 rounded-[24px] border border-danger/20 bg-danger/10 px-5 py-4 text-sm text-danger">
          {error}
        </div>
      )}

      {hasActiveRun && (
        <div className="mt-6 rounded-[24px] border border-accent/30 bg-accentSoft px-5 py-4 text-sm text-accent">
          This run is active on the worker. Some protected websites can take a few minutes before progress moves beyond 20%.
        </div>
      )}

      <div className="mt-6 rounded-[28px] border border-white/10 bg-surface p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-textMuted">While You Wait</p>
            <h2 className="mt-2 text-lg font-semibold text-textMain">Behind-the-scenes execution graph</h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-textMuted">
              {waitBoxMessage}
            </p>
          </div>
          <StatusBadge status={hasActiveRun ? 'running' : workflow.status === 'completed' ? 'success' : workflow.status === 'failed' ? 'fail' : 'pending'}>
            {hasActiveRun ? 'Worker active' : workflow.status === 'completed' ? 'Finished' : workflow.status === 'failed' ? 'Needs review' : 'Waiting'}
          </StatusBadge>
        </div>

        <div className="mt-6 grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-[24px] border border-white/10 bg-bg/70 p-4">
            <div className="grid gap-3 md:grid-cols-[repeat(5,minmax(0,1fr))]">
              {waitGraphSteps.map((step, index) => (
                <div key={step.title} className="relative">
                  <div className={`rounded-2xl border px-4 py-4 transition ${graphToneClasses[step.status] || graphToneClasses.pending}`}>
                    <p className="text-[11px] uppercase tracking-[0.18em] opacity-70">Step {index + 1}</p>
                    <p className="mt-2 text-base font-semibold">{step.title}</p>
                    <p className="mt-2 text-sm opacity-80">{step.caption}</p>
                  </div>
                  {index < waitGraphSteps.length - 1 && (
                    <div className="mx-auto hidden h-8 w-px bg-white/10 md:block" />
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[24px] border border-[#4f453a]/50 bg-[rgba(8,11,14,0.78)] p-4 shadow-inner">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-textMuted">Worker Actions</p>
                <p className="mt-2 text-sm text-textMuted">Simple code-style view of the current run.</p>
              </div>
              <div className="rounded-full border border-[#4f453a]/50 bg-white/5 px-3 py-1 text-xs text-textMuted">
                {progress}% progress
              </div>
            </div>
            <div className="mt-4 space-y-2 font-mono text-sm">
              {codeActions.map((item) => (
                <div
                  key={item.action}
                  className={`flex items-center justify-between rounded-xl border px-3 py-2 ${
                    item.state === 'done'
                      ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-200'
                      : item.state === 'active'
                        ? 'border-accent/30 bg-accent/10 text-accent'
                        : 'border-[#4f453a]/50 bg-white/[0.03] text-textMuted'
                  }`}
                >
                  <span>{item.action}</span>
                  <span className="text-[11px] uppercase tracking-[0.18em]">
                    {item.state === 'done' ? 'done' : item.state === 'active' ? 'live' : 'queued'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-8 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-white/10 bg-surface p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-textMuted">Execution Timeline</p>
                <h2 className="mt-2 text-lg font-semibold text-textMain">Live AI execution path</h2>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-textMuted">
                  Follow how the system decided on a strategy, extracted data, validated the output, checked retry conditions, and tracked memory usage.
                </p>
              </div>
              <StatusBadge status={workflow.status === 'completed' ? 'success' : workflow.status === 'failed' ? 'fail' : workflow.status || 'pending'}>
                {workflow.status || 'pending'}
              </StatusBadge>
            </div>
          </div>

          <div className="space-y-4">
          {timelineSteps.map((step) => (
            <PipelineStepCard
              key={step.title}
              title={step.title}
              status={step.status}
              description={step.description}
              detail={step.detail}
              metrics={step.metrics}
            />
          ))}
          </div>

          <div className="rounded-2xl border border-white/10 bg-surface p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-textMain">Validation Result</h3>
            <p className="mt-3 text-sm leading-6 text-textMuted">
              {validation.status === 'pass'
                ? 'The latest run passed validation and the output is ready for review.'
                : validation.status === 'fail'
                  ? 'The run failed before a clean validated output was confirmed.'
                  : 'Validation is waiting for extraction to finish.'}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <MetricChip
                label="Validation"
                value={validation.status || 'unknown'}
              />
              <MetricChip label="Confidence" value={formatConfidence(validation.confidence)} />
              <MetricChip label="Structured Records" value={data.length} />
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-surface p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-textMain">Retry Explanation</h3>
            <p className="mt-3 text-sm leading-6 text-textMuted">
              {retry.attempted
                ? 'A retry event was recorded in this run history.'
                : 'No retry event was recorded for this job view. The retry engine only activates when recovery is needed.'}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <MetricChip label="Retry Attempted" value={String(retry.attempted)} />
              <MetricChip label="Retry Result" value={retry.attempted ? (retry.result ? 'Recovered' : 'Still failed') : 'Skipped'} />
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-surface p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-textMain">Memory Usage</h3>
            <p className="mt-3 text-sm leading-6 text-textMuted">
              {memory.used
                ? 'The system reused a learned extraction pattern for this run.'
                : 'This run looks like a first-time domain attempt with generated selectors.'}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <MetricChip label="Memory Used" value={memory.used ? 'yes' : 'no'} />
              <MetricChip label="Selector Source" value={memory.selector_source || 'generated'} />
            </div>
          </div>
        </div>

        <ResultPreview
          workflow={workflow}
          description={
            extractedItemSummary === 'Extraction results will appear here'
              ? 'Review the structured output and execution intelligence from the latest run.'
              : extractedItemSummary
          }
        />
      </div>
    </div>
  );
};

export default JobDetailPage;
