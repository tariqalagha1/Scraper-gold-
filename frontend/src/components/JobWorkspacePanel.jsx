import React, { useCallback, useEffect, useMemo, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CircularProgress from '@mui/material/CircularProgress';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Typography from '@mui/material/Typography';
import AIExplanationCard from './AIExplanationCard';
import ExportStatusCard from './ExportStatusCard';
import ResultsWorkbench from './ResultsWorkbench';
import RunHeaderCard from './RunHeaderCard';
import RunProgressCard from './RunProgressCard';
import api from '../services/api';
import {
  buildExportMessage,
  humanizeLog,
} from '../assistant/orchestrator';
import { formatDate, formatStatus } from '../utils/helpers';

const POLL_INTERVAL_MS = 4000;

const JobWorkspacePanel = ({ jobId, embedded = false, onJobLoaded }) => {
  const [job, setJob] = useState(null);
  const [runs, setRuns] = useState([]);
  const [results, setResults] = useState([]);
  const [logs, setLogs] = useState([]);
  const [tabIndex, setTabIndex] = useState(0);
  const [loading, setLoading] = useState(Boolean(jobId));
  const [startingRun, setStartingRun] = useState(false);
  const [retryingRun, setRetryingRun] = useState(false);
  const [exportMessage, setExportMessage] = useState('');
  const [exportMeta, setExportMeta] = useState(null);
  const [error, setError] = useState('');

  const latestRun = runs[0] || null;
  const activeRun = useMemo(
    () => (latestRun && ['pending', 'running'].includes(latestRun.status) ? latestRun : null),
    [latestRun]
  );

  const loadJobData = useCallback(
    async ({ silent = false } = {}) => {
      if (!jobId) {
        setJob(null);
        setRuns([]);
        setResults([]);
        setLogs([]);
        setLoading(false);
        return;
      }

      if (!silent) {
        setLoading(true);
      }

      try {
        const [jobData, runsData] = await Promise.all([api.getJob(jobId), api.getRunsByJob(jobId)]);
        setJob(jobData);
        setRuns(runsData);
        if (onJobLoaded) {
          onJobLoaded(jobData, runsData);
        }

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
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load workspace');
      } finally {
        if (!silent) {
          setLoading(false);
        }
      }
    },
    [jobId, onJobLoaded]
  );

  useEffect(() => {
    loadJobData();
  }, [loadJobData]);

  useEffect(() => {
    if (!activeRun) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      loadJobData({ silent: true });
    }, POLL_INTERVAL_MS);

    return () => window.clearTimeout(timer);
  }, [activeRun, loadJobData]);

  const handleStartRun = async () => {
    if (!jobId) {
      return;
    }

    try {
      setStartingRun(true);
      setError('');
      const createdRun = await api.startJobRun(jobId);
      setRuns((previousRuns) => [createdRun, ...previousRuns.filter((run) => run.id !== createdRun.id)]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start run');
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
      const createdRun = await api.retryRun(latestRun.id);
      setRuns((previousRuns) => [createdRun, ...previousRuns.filter((run) => run.id !== createdRun.id)]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to retry run');
    } finally {
      setRetryingRun(false);
    }
  };

  const handleExport = async (runId, format) => {
    if (!runId) {
      return;
    }

    try {
      await api.createExport({ run_id: runId, format });
      setExportMessage(buildExportMessage(format));
      setExportMeta({
        file_name: `run-${runId}.${format === 'excel' ? 'xlsx' : format === 'word' ? 'docx' : format}`,
        file_size: null,
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Export failed');
    }
  };

  if (!jobId) {
    return (
      <Card sx={{ borderRadius: 4, minHeight: 320 }}>
        <CardContent>
          <Stack spacing={2} justifyContent="center" sx={{ minHeight: 260 }}>
            <Typography variant="h5">Run Workspace</Typography>
            <Typography color="text.secondary">
              Choose a job from the dashboard or start a new request to open its live workspace here.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card sx={{ borderRadius: 4 }}>
        <CardContent>
          <Stack spacing={2} alignItems="center" sx={{ py: 6 }}>
            <CircularProgress />
            <Typography variant="h6">Loading workspace</Typography>
            <Typography color="text.secondary" align="center">
              We are pulling the latest job, run, log, and result details for you.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    );
  }

  if (!job) {
    return (
      <Card sx={{ borderRadius: 4 }}>
        <CardContent>
          <Stack spacing={1.5}>
            <Typography variant="h6">Job not found</Typography>
            <Typography color="text.secondary">
              This job may have been removed or is no longer available in your workspace.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    );
  }

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant={embedded ? 'h5' : 'h4'} gutterBottom>
          Run Workspace
        </Typography>
        <Typography color="text.secondary">
          The assistant is doing the work, and you can follow it clearly here.
        </Typography>
      </Box>

      <RunHeaderCard
        job={job}
        latestRun={latestRun}
        activeRun={activeRun}
        startingRun={startingRun}
        retryingRun={retryingRun}
        onStartRun={handleStartRun}
        onRetryRun={handleRetryRun}
      />

      {error && <Alert severity="error">{error}</Alert>}

      <AIExplanationCard run={latestRun} results={results} logs={logs} />

      <RunProgressCard run={latestRun} logs={logs} />

      <ExportStatusCard
        run={latestRun}
        exportMessage={exportMessage}
        exportMeta={exportMeta}
        onExport={handleExport}
      />

      <Tabs
        value={tabIndex}
        onChange={(event, value) => setTabIndex(value)}
        variant="scrollable"
        allowScrollButtonsMobile
        sx={{ bgcolor: 'background.paper', borderRadius: 3, px: 1 }}
      >
        <Tab label="Results" />
        <Tab label="Run History" />
        <Tab label="Live Steps" />
      </Tabs>

      {tabIndex === 0 && <ResultsWorkbench results={results} />}

      {tabIndex === 1 && (
        <Stack spacing={2}>
          {runs.length === 0 ? (
            <Typography>No runs yet</Typography>
          ) : (
            runs.map((run) => (
              <Card key={run.id} sx={{ borderRadius: 4 }}>
                <CardContent>
                  <Typography variant="subtitle1">Run #{run.id}</Typography>
                  <Typography>Status: {formatStatus(run.status)}</Typography>
                  <Typography>Progress: {run.progress ?? 0}%</Typography>
                  <Typography variant="body2">Started: {formatDate(run.started_at)}</Typography>
                  <Typography variant="body2">Finished: {formatDate(run.finished_at)}</Typography>
                  {run.error_message && (
                    <Typography variant="body2" color="error">
                      {run.error_message}
                    </Typography>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </Stack>
      )}

      {tabIndex === 2 && (
        <Card sx={{ borderRadius: 4 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Friendly Run Log
            </Typography>
            {logs.length === 0 ? (
              <Typography>No run events yet</Typography>
            ) : (
              <List disablePadding>
                {logs.map((entry, index) => (
                  <ListItem key={`${entry.timestamp}-${entry.event}-${index}`} divider>
                    <ListItemText
                      primary={humanizeLog(entry)}
                      secondary={formatDate(entry.timestamp)}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </CardContent>
        </Card>
      )}
    </Stack>
  );
};

export default JobWorkspacePanel;
