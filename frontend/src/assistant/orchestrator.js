const RECENT_REQUESTS_KEY = 'recent_requests';

export const detectScrapeType = (text) => {
  const value = (text || '').toLowerCase();

  if (value.includes('pdf') || value.includes('document') || value.includes('download all pdf')) {
    return 'pdf';
  }
  if (value.includes('image') || value.includes('photo') || value.includes('gallery')) {
    return 'images';
  }
  if (
    value.includes('price') ||
    value.includes('product') ||
    value.includes('availability') ||
    value.includes('catalog') ||
    value.includes('table') ||
    value.includes('listing') ||
    value.includes('patient') ||
    value.includes('name') ||
    value.includes('mobile') ||
    value.includes('phone') ||
    value.includes('national id') ||
    value.includes('id number')
  ) {
    return 'structured';
  }

  return 'general';
};

export const explainIntent = (scrapeType) => {
  switch (scrapeType) {
    case 'structured':
      return 'This looks like a product or structured data extraction task.';
    case 'pdf':
      return 'This looks like a document collection task.';
    case 'images':
      return 'This looks like an image collection task.';
    default:
      return 'This looks like a general website content extraction task.';
  }
};

export const buildIntentTitle = (prompt, url) => {
  if (prompt?.trim()) return prompt.trim();
  if (url?.trim()) return `Scrape ${url.trim()}`;
  return 'New scraping request';
};

export const interpretCommand = ({ url, prompt }) => {
  const scrapeType = detectScrapeType(prompt);
  return {
    url,
    prompt,
    scrape_type: scrapeType,
    explanation: explainIntent(scrapeType),
    title: buildIntentTitle(prompt, url),
  };
};

export const getRecentRequests = () => {
  try {
    return JSON.parse(localStorage.getItem(RECENT_REQUESTS_KEY) || '[]');
  } catch {
    return [];
  }
};

export const saveRecentRequest = (request) => {
  const current = getRecentRequests();
  const next = [
    request,
    ...current.filter((item) => item.url !== request.url || item.prompt !== request.prompt),
  ].slice(0, 5);
  localStorage.setItem(RECENT_REQUESTS_KEY, JSON.stringify(next));
  return next;
};

export const humanizeLog = (entry) => {
  const map = {
    run_started: 'Starting your request',
    pipeline_started: 'Scanning pages and extracting data',
    pipeline_finished: 'Finished scanning the website',
    persisting_results: 'Saving the results for review',
    run_completed: 'Everything is ready',
    timeout: 'The website took too long to respond',
    run_failed: 'The run could not finish',
    retry_requested: 'Trying the request again',
    duplicate_blocked: 'Another run was already in progress',
  };

  return map[entry?.event] || entry?.message || 'Working on your request';
};

export const buildRunStatusMessage = (run) => {
  if (!run) return 'Ready when you are.';
  if (run.status === 'pending' || run.status === 'running') {
    return 'Scanning pages and extracting data.';
  }
  if (run.status === 'completed') {
    return 'This run has finished and your results are ready to review.';
  }
  return 'This run stopped before it could fully complete.';
};

export const buildResultHighlights = (results) => {
  const first = results?.[0]?.data_json || {};
  return {
    name: first.name || first.title || first.product_name || '',
    price: first.price || first.amount || '',
    availability: first.availability || first.stock || '',
  };
};

export const buildResultFieldSummary = (results) => {
  const items = results || [];
  const keys = [...new Set(items.flatMap((item) => Object.keys(item?.data_json || {})))];
  const preferredKeys = ['name', 'title', 'price', 'amount', 'availability', 'stock'];
  const visibleKeys = preferredKeys.filter((key) => keys.includes(key));

  if (visibleKeys.length > 0) {
    return `Key fields available: ${visibleKeys.join(', ')}.`;
  }

  if (keys.length > 0) {
    return `We found ${Math.min(keys.length, 5)} common fields in the results.`;
  }

  return 'No structured fields are available yet.';
};

export const buildResultSummary = (items) => {
  const results = items || [];
  const total = results.length;
  const prices = results
    .map((item) => {
      const raw = item?.data_json?.price || item?.data_json?.amount;
      if (typeof raw === 'number') return raw;
      const match = String(raw || '').match(/(\d+(\.\d+)?)/);
      return match ? Number(match[1]) : null;
    })
    .filter((value) => Number.isFinite(value));

  if (prices.length > 0) {
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    return `${total} item${total === 1 ? '' : 's'} found. Most prices appear to fall between $${min} and $${max}.`;
  }

  return `${total} item${total === 1 ? '' : 's'} found.`;
};

export const buildRunExplanation = ({ run, results, logs }) => {
  const count = results?.length || 0;
  const lastStep = logs?.length ? humanizeLog(logs[logs.length - 1]) : '';

  if (!run) {
    return {
      title: 'Ready to begin',
      severity: 'info',
      whatHappened: 'No scraping run has started yet.',
      whatWasFound: 'No results yet.',
      whatItMeans: 'The request is ready whenever you are.',
      nextStep: 'Click Start Run to begin collecting data.',
      suggestions: ['Start the run', 'Try a clear request like “find product prices”'],
    };
  }

  if (run.status === 'pending' || run.status === 'running') {
    return {
      title: 'Your request is in progress',
      severity: 'info',
      whatHappened: lastStep || 'We are scanning pages and extracting the information you asked for.',
      whatWasFound: count ? `We already collected ${count} item${count === 1 ? '' : 's'} so far.` : 'Results are still being gathered.',
      whatItMeans: 'The task is still active and may continue updating.',
      nextStep: 'Stay on this page while we finish the run.',
      suggestions: ['Wait for the run to finish', 'Open the results tab to watch data appear'],
    };
  }

  if (run.status === 'completed') {
    return {
      title: 'Scraping completed successfully',
      severity: 'success',
      whatHappened: lastStep || 'The run finished and the website was processed.',
      whatWasFound: `We found ${count} item${count === 1 ? '' : 's'}.`,
      whatItMeans: count ? 'Your data is ready to review, search, and export.' : 'The website was reached, but there was little or no matching data to show.',
      nextStep: count ? 'Review the summary below and export the results if needed.' : 'Try a more specific request or a different page from the same site.',
      suggestions: count ? ['Search the results', 'Export the data', 'Retry if you need fresher data'] : ['Retry the run', 'Try a more specific page'],
    };
  }

  if (count > 0) {
    return {
      title: 'The run finished with some issues',
      severity: 'warning',
      whatHappened: lastStep || 'The request stopped before every page could be processed.',
      whatWasFound: `We still collected ${count} item${count === 1 ? '' : 's'} before it stopped.`,
      whatItMeans: run.error_message || 'You may already have useful data, even though the run was not fully complete.',
      nextStep: 'Review the results first, then decide whether to retry for more coverage.',
      suggestions: ['Review the results', 'Retry the run', 'Export what you already have'],
    };
  }

  return {
    title: 'The run needs attention',
    severity: 'warning',
    whatHappened: lastStep || 'The request did not finish normally.',
    whatWasFound: count ? `Some data was collected before the run stopped. ${count} item${count === 1 ? '' : 's'} found.` : 'No usable data was collected.',
    whatItMeans: run.error_message || 'The website may have blocked access or taken too long to respond.',
    nextStep: 'Try again, use a simpler page, or retry the run.',
    suggestions: ['Retry the run', 'Try a simpler page', 'Use a more specific request'],
  };
};

export const buildExportMessage = (format) =>
  `Your ${String(format || '').toUpperCase()} export is being prepared. You can download it from Exports once it is ready.`;

export const buildActivityFeed = ({ jobs = [], runs = [], exports = [] }) => {
  const jobItems = jobs.map((job) => ({
    id: job.id,
    type: 'job',
    type_label: 'Job',
    title: `New job for ${job.url}`,
    subtitle: `Scrape type: ${job.scrape_type}`,
    timestamp: job.created_at,
    status: null,
    status_color: 'default',
  }));

  const runItems = runs.map((run) => ({
    id: run.id,
    type: 'run',
    type_label: 'Run',
    title: `Run for job ${run.job_id}`,
    subtitle: run.error_message || `Progress ${run.progress ?? 0}%`,
    timestamp: run.finished_at || run.started_at || run.created_at,
    status: run.status,
    status_color:
      run.status === 'completed'
        ? 'success'
        : run.status === 'failed'
          ? 'error'
          : run.status === 'running'
            ? 'info'
            : 'warning',
  }));

  const exportItems = exports.map((exportItem) => ({
    id: exportItem.id,
    type: 'export',
    type_label: 'Export',
    title: `${String(exportItem.format || 'file').toUpperCase()} export created`,
    subtitle: exportItem.file_path?.split('/').pop() || `Run ${exportItem.run_id}`,
    timestamp: exportItem.created_at,
    status: exportItem.file_path ? 'ready' : 'pending',
    status_color: exportItem.file_path ? 'success' : 'warning',
  }));

  return [...runItems, ...exportItems, ...jobItems]
    .filter((item) => item.timestamp)
    .sort((left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime())
    .slice(0, 8);
};

export const buildWorkspaceHealth = ({ runs = [] }) => {
  const activeRuns = runs.filter((run) => ['pending', 'running'].includes(run.status)).length;
  const failedRuns = runs.filter((run) => run.status === 'failed').length;
  const completedRuns = runs.filter((run) => run.status === 'completed').length;

  if (activeRuns > 0) {
    return {
      label: 'Active',
      color: 'info',
      activeRuns,
      failedRuns,
      message: 'Work is currently in progress. Keep an eye on active runs and recent failures.',
    };
  }

  if (failedRuns > completedRuns && failedRuns > 0) {
    return {
      label: 'Needs attention',
      color: 'warning',
      activeRuns,
      failedRuns,
      message: 'Recent failures are outweighing successful runs. It may be time to review blocked pages or retry key jobs.',
    };
  }

  return {
    label: 'Healthy',
    color: 'success',
    activeRuns,
    failedRuns,
    message: 'Recent activity looks stable, and there are no active issues competing for attention right now.',
  };
};
