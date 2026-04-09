const ensureObject = (value) => (value && typeof value === 'object' && !Array.isArray(value) ? value : {});
const ensureArray = (value) => (Array.isArray(value) ? value : []);

const coerceNumber = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const toIsoDate = (value) => {
  if (!value) return '';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '' : parsed.toISOString();
};

export const formatDurationMs = (value) => {
  const duration = coerceNumber(value, 0);
  if (duration <= 0) return 'Not available';
  if (duration < 1000) return `${duration} ms`;
  return `${(duration / 1000).toFixed(2)} s`;
};

export const formatConfidence = (value) => {
  const confidence = coerceNumber(value, 0);
  if (confidence <= 0) return 'Unknown';
  return `${confidence.toFixed(2)} confidence`;
};

export const getValidationTone = (status) => {
  const normalized = String(status || 'unknown').toLowerCase();
  if (normalized === 'pass') return 'success';
  if (normalized === 'fail') return 'fail';
  return 'pending';
};

export const getRetryTone = (retry) => (retry?.attempted ? 'running' : 'skipped');
export const getMemoryTone = (memory) => (memory?.used ? 'accent' : 'skipped');

const isNormalizedWorkflow = (value) => {
  const payload = ensureObject(value);
  return (
    Object.prototype.hasOwnProperty.call(payload, 'request') &&
    Object.prototype.hasOwnProperty.call(payload, 'result') &&
    Object.prototype.hasOwnProperty.call(payload, 'execution') &&
    Object.prototype.hasOwnProperty.call(payload, 'metadata')
  );
};

const calculateDurationMs = (startedAt, finishedAt) => {
  const started = startedAt ? new Date(startedAt) : null;
  const finished = finishedAt ? new Date(finishedAt) : null;
  if (!started || !finished || Number.isNaN(started.getTime()) || Number.isNaN(finished.getTime())) {
    return 0;
  }
  return Math.max(0, finished.getTime() - started.getTime());
};

const extractStructuredItemsFromPayload = (payload) => {
  if (Array.isArray(payload)) {
    return payload.filter((item) => item && typeof item === 'object');
  }

  if (!payload || typeof payload !== 'object') {
    return [];
  }

  if (Array.isArray(payload.items)) {
    return payload.items.filter((item) => item && typeof item === 'object');
  }

  const nestedLists = Object.values(payload).filter(
    (value) => Array.isArray(value) && value.every((item) => item && typeof item === 'object')
  );
  if (nestedLists.length > 0) {
    return nestedLists.sort((left, right) => right.length - left.length)[0];
  }

  if (Object.keys(payload).length > 0 && !payload.summary && !payload.page_type && !payload.cleaned_text) {
    return [payload];
  }

  return [];
};

const flattenResults = (results) =>
  ensureArray(results).flatMap((entry) => extractStructuredItemsFromPayload(entry?.data_json));

export const buildWorkflowContract = ({ workflow, job, run, results = [], logs = [] } = {}) => {
  if (isNormalizedWorkflow(workflow)) {
    return {
      status: String(workflow.status || 'failed'),
      request: {
        url: String(workflow.request?.url || ''),
        scrape_type: String(workflow.request?.scrape_type || ''),
        config: ensureObject(workflow.request?.config),
        strategy: ensureObject(workflow.request?.strategy),
        credentials: ensureObject(workflow.request?.credentials),
      },
      result: {
        data: ensureArray(workflow.result?.data),
        raw: ensureObject(workflow.result?.raw),
        processed: ensureObject(workflow.result?.processed),
        analysis: ensureObject(workflow.result?.analysis),
        vector: ensureObject(workflow.result?.vector),
        exports: ensureObject(workflow.result?.exports),
      },
      execution: {
        decision: {
          page_type: String(workflow.execution?.decision?.page_type || 'unknown'),
          confidence: coerceNumber(workflow.execution?.decision?.confidence, 0),
          reason: String(workflow.execution?.decision?.reason || ''),
        },
        validation: {
          status: String(workflow.execution?.validation?.status || 'unknown'),
          confidence: coerceNumber(workflow.execution?.validation?.confidence, 0),
          issues: ensureArray(workflow.execution?.validation?.issues),
          metrics: ensureObject(workflow.execution?.validation?.metrics),
          should_retry: Boolean(workflow.execution?.validation?.should_retry),
        },
        retry: {
          attempted: Boolean(workflow.execution?.retry?.attempted),
          result: Boolean(workflow.execution?.retry?.result),
        },
        memory: {
          used: Boolean(workflow.execution?.memory?.used),
          selector_source: String(workflow.execution?.memory?.selector_source || 'generated'),
          success_rate: workflow.execution?.memory?.success_rate ?? null,
        },
        timing: ensureObject(workflow.execution?.timing),
        steps: {
          current: String(workflow.execution?.steps?.current || ''),
          progress: coerceNumber(workflow.execution?.steps?.progress, 0),
        },
        trace: ensureObject(workflow.execution?.trace),
      },
      errors: ensureArray(workflow.errors),
      metadata: {
        job_id: String(workflow.metadata?.job_id || ''),
        run_id: String(workflow.metadata?.run_id || ''),
        user_id: String(workflow.metadata?.user_id || ''),
        started_at: toIsoDate(workflow.metadata?.started_at),
        finished_at: toIsoDate(workflow.metadata?.finished_at),
        duration_ms: coerceNumber(workflow.metadata?.duration_ms, 0),
      },
    };
  }

  const structuredData = flattenResults(results);
  const primaryProcessedPayload = ensureObject(results[0]?.data_json);
  const retryAttempted = ensureArray(logs).some((entry) => entry?.event === 'retry_requested');
  const runStatus = String(run?.status || workflow?.status || 'idle');
  const validationStatus =
    runStatus === 'completed' ? 'pass' : runStatus === 'failed' ? 'fail' : runStatus === 'running' ? 'pending' : 'unknown';
  const pageType = String(primaryProcessedPayload.page_type || structuredData[0]?.page_type || 'unknown');
  const decisionReason =
    pageType === 'unknown'
      ? 'Decision details are not exposed by this API response yet.'
      : 'Decision details are inferred from the current run snapshot.';
  const startedAt = run?.started_at || workflow?.metadata?.started_at || '';
  const finishedAt = run?.finished_at || workflow?.metadata?.finished_at || '';

  return {
    status: runStatus,
    request: {
      url: String(job?.url || workflow?.request?.url || ''),
      scrape_type: String(job?.scrape_type || workflow?.request?.scrape_type || ''),
      config: ensureObject(job?.config || workflow?.request?.config),
      strategy: ensureObject(workflow?.request?.strategy),
      credentials: ensureObject(workflow?.request?.credentials),
    },
    result: {
      data: structuredData,
      raw: ensureObject(workflow?.result?.raw),
      processed: primaryProcessedPayload,
      analysis: ensureObject(workflow?.result?.analysis),
      vector: ensureObject(workflow?.result?.vector),
      exports: ensureObject(workflow?.result?.exports),
    },
    execution: {
      decision: {
        page_type: pageType,
        confidence: coerceNumber(workflow?.execution?.decision?.confidence, 0),
        reason: String(workflow?.execution?.decision?.reason || decisionReason),
      },
      validation: {
        status: String(workflow?.execution?.validation?.status || validationStatus),
        confidence: coerceNumber(workflow?.execution?.validation?.confidence, validationStatus === 'pass' ? 0.75 : 0),
        issues:
          ensureArray(workflow?.execution?.validation?.issues).length > 0
            ? ensureArray(workflow?.execution?.validation?.issues)
            : run?.error_message
              ? [run.error_message]
              : [],
        metrics:
          Object.keys(ensureObject(workflow?.execution?.validation?.metrics)).length > 0
            ? ensureObject(workflow?.execution?.validation?.metrics)
            : {
                records: structuredData.length,
                fill_ratio: structuredData.length > 0 ? 1 : 0,
                duplicate_ratio: 0,
              },
        should_retry: Boolean(workflow?.execution?.validation?.should_retry ?? runStatus === 'failed'),
      },
      retry: {
        attempted: Boolean(workflow?.execution?.retry?.attempted ?? retryAttempted),
        result: Boolean(workflow?.execution?.retry?.result ?? (retryAttempted && runStatus === 'completed')),
      },
      memory: {
        used: Boolean(workflow?.execution?.memory?.used),
        selector_source: String(workflow?.execution?.memory?.selector_source || 'generated'),
        success_rate: workflow?.execution?.memory?.success_rate ?? null,
      },
      timing: ensureObject(workflow?.execution?.timing),
      steps: {
        current: String(workflow?.execution?.steps?.current || runStatus),
        progress: coerceNumber(workflow?.execution?.steps?.progress, run?.progress ?? 0),
      },
      trace: ensureObject(workflow?.execution?.trace),
    },
    errors: ensureArray(workflow?.errors).length > 0 ? ensureArray(workflow.errors) : run?.error_message ? [run.error_message] : [],
    metadata: {
      job_id: String(job?.id || run?.job_id || workflow?.metadata?.job_id || ''),
      run_id: String(run?.id || workflow?.metadata?.run_id || ''),
      user_id: String(workflow?.metadata?.user_id || ''),
      started_at: toIsoDate(startedAt),
      finished_at: toIsoDate(finishedAt),
      duration_ms: coerceNumber(workflow?.metadata?.duration_ms, calculateDurationMs(startedAt, finishedAt)),
    },
  };
};
