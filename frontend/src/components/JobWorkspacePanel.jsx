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
const SECONDARY_TEXT_COLOR = 'rgba(226, 226, 227, 0.72)';
const EXPORT_POLL_INTERVAL_MS = 2500;
const EXPORT_POLL_TIMEOUT_MS = 60000;
const workspaceCardSx = {
  borderRadius: 4,
  bgcolor: 'rgba(28, 31, 35, 0.84)',
  border: '1px solid rgba(79, 69, 58, 0.5)',
  color: '#E2E2E3',
  boxShadow: 'none',
  '& .MuiTypography-colorTextSecondary': {
    color: SECONDARY_TEXT_COLOR,
  },
  '& .MuiListItemText-secondary': {
    color: SECONDARY_TEXT_COLOR,
  },
};

const triggerBlobDownload = (download, fallbackFilename) => {
  const blob = download?.blob instanceof Blob ? download.blob : new Blob([download?.blob ?? '']);
  const filename = String(download?.filename || fallbackFilename || 'download').trim() || 'download';
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(anchor);
};

const JobWorkspacePanel = ({ jobId, embedded = false, onJobLoaded }) => {
  const [job, setJob] = useState(null);
  const [runs, setRuns] = useState([]);
  const [results, setResults] = useState([]);
  const [logs, setLogs] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
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
        setSystemHealth(null);
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
        try {
          const healthData = await api.getHealth();
          setSystemHealth(healthData);
        } catch (healthError) {
          setSystemHealth(null);
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
      const createdRun = await api.startJobRun(jobId, { job });
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
      const exportPayload = await api.createExport({ run_id: runId, format });
      const exportId = exportPayload?.id;
      const status = String(exportPayload?.status || '').toLowerCase();
      const extension = format === 'excel' ? 'xlsx' : format === 'word' ? 'docx' : format;
      const fallbackFileName = `run-${runId}.${extension}`;

      if (exportId && status === 'completed') {
        const download = await api.downloadExport(exportId);
        triggerBlobDownload(download, fallbackFileName);
        setExportMessage(`Your ${String(format || '').toUpperCase()} export is ready and downloading now.`);
      } else if (exportId) {
        const startedAt = Date.now();
        let completed = false;
        while (Date.now() - startedAt < EXPORT_POLL_TIMEOUT_MS) {
          await new Promise((resolve) => {
            window.setTimeout(resolve, EXPORT_POLL_INTERVAL_MS);
          });
          const refreshed = await api.getExportStatus(exportId);
          const refreshedStatus = String(refreshed?.status || '').toLowerCase();
          if (refreshedStatus === 'completed') {
            const download = await api.downloadExport(exportId);
            triggerBlobDownload(download, fallbackFileName);
            setExportMessage(`Your ${String(format || '').toUpperCase()} export is ready and downloading now.`);
            completed = true;
            break;
          }
          if (refreshedStatus === 'failed') {
            setError('Export failed while generating the file.');
            completed = true;
            break;
          }
        }
        if (!completed) {
          setExportMessage(buildExportMessage(format));
        }
      } else {
        setExportMessage(buildExportMessage(format));
      }

      setExportMeta({
        file_name: fallbackFileName,
        file_size: exportPayload?.file_size || null,
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Export failed');
    }
  };

  if (!jobId) {
    return (
      <Card sx={{ ...workspaceCardSx, minHeight: 320 }}>
        <CardContent>
          <Stack spacing={2} justifyContent="center" sx={{ minHeight: 260 }}>
            <Typography variant="h5">Run Workspace</Typography>
            <Typography color="text.secondary" sx={{ color: SECONDARY_TEXT_COLOR }}>
              Choose a job from the dashboard or start a new request to open its live workspace here.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card sx={workspaceCardSx}>
        <CardContent>
          <Stack spacing={2} alignItems="center" sx={{ py: 6 }}>
            <CircularProgress />
            <Typography variant="h6">Loading workspace</Typography>
            <Typography color="text.secondary" align="center" sx={{ color: SECONDARY_TEXT_COLOR }}>
              We are pulling the latest job, run, log, and result details for you.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    );
  }

  if (!job) {
    return (
      <Card sx={workspaceCardSx}>
        <CardContent>
          <Stack spacing={1.5}>
            <Typography variant="h6">Job not found</Typography>
            <Typography color="text.secondary" sx={{ color: SECONDARY_TEXT_COLOR }}>
              This job may have been removed or is no longer available in your workspace.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    );
  }

  return (
    <Stack
      spacing={3}
      sx={{
        color: '#E2E2E3',
        '& .MuiTypography-colorTextSecondary': { color: SECONDARY_TEXT_COLOR },
        '& .MuiListItemText-secondary': { color: SECONDARY_TEXT_COLOR },
      }}
    >
      <Box>
        <Typography variant={embedded ? 'h5' : 'h4'} gutterBottom>
          Run Workspace
        </Typography>
        <Typography color="text.secondary" sx={{ color: SECONDARY_TEXT_COLOR }}>
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

      <RunProgressCard run={latestRun} logs={logs} results={results} systemHealth={systemHealth} />

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
        sx={{
          bgcolor: 'rgba(28, 31, 35, 0.84)',
          border: '1px solid rgba(79, 69, 58, 0.5)',
          borderRadius: 3,
          px: 1,
          '& .MuiTab-root': {
            color: SECONDARY_TEXT_COLOR,
          },
          '& .MuiTab-root.Mui-selected': {
            color: '#F0BD7F',
          },
          '& .MuiTabs-indicator': {
            backgroundColor: '#F0BD7F',
          },
        }}
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
              <Card key={run.id} sx={workspaceCardSx}>
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
        <Card sx={workspaceCardSx}>
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
