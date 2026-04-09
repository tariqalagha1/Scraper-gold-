import React, { useCallback, useEffect, useMemo, useState } from 'react';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { useNavigate } from 'react-router-dom';
import AICommandPanel from '../components/AICommandPanel';
import QuickStatusCards from '../components/QuickStatusCards';
import ResultsWorkbench from '../components/ResultsWorkbench';
import RecentRunsCard from '../components/RecentRunsCard';
import RecentRequestsCard from '../components/RecentRequestsCard';
import SectionHeader from '../components/SectionHeader';
import api from '../services/api';
import { getRecentRequests } from '../assistant/orchestrator';
import {
  clearLandingExtractionIntent,
  readLandingExtractionIntent,
  storeLandingExtractionIntent,
} from '../utils/extractionIntent';
import { getErrorMessage } from '../utils/helpers';
import { buildWorkflowContract } from '../utils/workflowContract';

const ACTIVE_RUN_POLL_INTERVAL_MS = 4000;

const sortRunsByRecency = (runs = []) =>
  [...runs].sort((left, right) => {
    const leftTime = new Date(left.finished_at || left.started_at || left.created_at || 0).getTime();
    const rightTime = new Date(right.finished_at || right.started_at || right.created_at || 0).getTime();
    return rightTime - leftTime;
  });

const buildLatestRunsByJob = (runs = []) =>
  sortRunsByRecency(runs).reduce((accumulator, run) => {
    if (!accumulator[run.job_id]) {
      accumulator[run.job_id] = run;
    }
    return accumulator;
  }, {});

const DashboardPage = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [runs, setRuns] = useState([]);
  const [accountSummary, setAccountSummary] = useState(null);
  const [results, setResults] = useState([]);
  const [recentRequests, setRecentRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [commandDefaults, setCommandDefaults] = useState({
    url: '',
    prompt: '',
    key: 'default',
  });

  const sortedRuns = useMemo(() => sortRunsByRecency(runs), [runs]);
  const latestRun = sortedRuns[0] || null;
  const latestRunsByJob = useMemo(() => buildLatestRunsByJob(sortedRuns), [sortedRuns]);
  const latestJob = useMemo(
    () => jobs.find((item) => item.id === latestRun?.job_id) || null,
    [jobs, latestRun]
  );
  const latestWorkflow = useMemo(
    () =>
      buildWorkflowContract({
        job: latestJob,
        run: latestRun,
        results,
      }),
    [latestJob, latestRun, results]
  );

  const loadDashboardData = useCallback(
    async ({ silent = false } = {}) => {
      if (!silent) {
        setLoading(true);
      }

      try {
        const [jobItems, runItems, summaryData] = await Promise.all([
          api.getJobs(),
          api.getRuns(),
          api.getAccountSummary(),
        ]);

        setJobs(jobItems);
        setRuns(runItems);
        setAccountSummary(summaryData);

        const mostRecentRun = sortRunsByRecency(runItems)[0] || null;
        if (mostRecentRun) {
          const latestResults = await api.getResults(mostRecentRun.id);
          setResults(latestResults);
        } else {
          setResults([]);
        }

        setRecentRequests(getRecentRequests());
        setError('');
      } catch (requestError) {
        setError(getErrorMessage(requestError, 'Could not load the dashboard right now.'));
      } finally {
        if (!silent) {
          setLoading(false);
        }
      }
    },
    []
  );

  useEffect(() => {
    const intent = readLandingExtractionIntent();
    if (!intent) {
      return;
    }

    if (intent.requiresLogin) {
      navigate('/jobs/new', { replace: true });
      return;
    }

    setCommandDefaults({
      url: intent.url,
      prompt: intent.prompt,
      key: `landing-intent-${Date.now()}`,
    });
    clearLandingExtractionIntent();
  }, [navigate]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  useEffect(() => {
    if (!latestRun || !['pending', 'running'].includes(latestRun.status)) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      loadDashboardData({ silent: true });
    }, ACTIVE_RUN_POLL_INTERVAL_MS);

    return () => window.clearTimeout(timer);
  }, [latestRun, loadDashboardData]);

  const handleStartRun = (preview, prompt) => {
    setError('');
    storeLandingExtractionIntent({
      url: preview.url,
      prompt,
      scrape_type: preview.scrape_type,
      max_pages: 10,
      follow_pagination: true,
      requiresLogin: false,
    });
    navigate('/jobs/new');
  };

  const handleReuseRequest = (request) => {
    setCommandDefaults({
      url: request.url || '',
      prompt: request.prompt || '',
      key: `${request.url || 'request'}-${request.prompt || 'prompt'}-${Date.now()}`,
    });
  };

  if (loading) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-7xl items-center justify-center px-6 py-12 lg:px-8">
        <Stack spacing={2} alignItems="center">
          <CircularProgress sx={{ color: '#FFD3A0' }} />
          <Typography sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>Loading workspace...</Typography>
        </Stack>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-12 lg:px-8 lg:py-16">
      <SectionHeader
        eyebrow="Scraping Workspace"
        title="Run and Review Jobs"
        description="Start a scrape, watch recent runs, inspect the latest results, and quickly reuse past requests from one dashboard."
      />

      {error && (
        <div className="mt-8">
          <Alert
            severity="error"
            sx={{
              borderRadius: 3,
              backgroundColor: 'rgba(255,111,145,0.10)',
              color: '#FBE8EE',
              border: '1px solid rgba(255,111,145,0.25)',
            }}
          >
            {error}
          </Alert>
        </div>
      )}

      <div className="mt-8 space-y-8">
        <div className="rounded-2xl border border-white/10 bg-surface p-1">
          <AICommandPanel
            key={commandDefaults.key}
            initialUrl={commandDefaults.url}
            initialPrompt={commandDefaults.prompt}
            onStart={handleStartRun}
          />
          <div className="flex items-center gap-2 px-5 pb-5 text-sm text-textMuted">
            <AutoAwesomeIcon sx={{ fontSize: 18, color: '#FFD3A0' }} />
            Review the detected scrape type, confirm the request, then continue into the job flow.
          </div>
        </div>

        <QuickStatusCards jobs={jobs} runs={runs} accountSummary={accountSummary} />

        <div className="grid grid-cols-1 gap-8 xl:grid-cols-[1.4fr_0.6fr]">
          <ResultsWorkbench results={latestWorkflow.result?.data || []} />
          <RecentRunsCard jobs={jobs} latestRunsByJob={latestRunsByJob} />
        </div>

        <RecentRequestsCard requests={recentRequests} onReuse={handleReuseRequest} />
      </div>
    </div>
  );
};

export default DashboardPage;
