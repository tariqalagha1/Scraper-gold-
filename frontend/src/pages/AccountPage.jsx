import React, { useEffect, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import ActivityFeedCard from '../components/ActivityFeedCard';
import WorkspaceHealthCard from '../components/WorkspaceHealthCard';
import { buildActivityFeed, buildWorkspaceHealth } from '../assistant/orchestrator';
import api from '../services/api';

const AccountPage = () => {
  const [summary, setSummary] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [runs, setRuns] = useState([]);
  const [exports, setExports] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api.getAccountSummary(), api.getJobs(), api.getRuns(), api.getExports()])
      .then(([summaryData, jobItems, runItems, exportItems]) => {
        setSummary(summaryData);
        setJobs(jobItems);
        setRuns(runItems);
        setExports(exportItems);
        setError('');
      })
      .catch(() => {
        setSummary(null);
        setError('We could not load your account details right now.');
      });
  }, []);

  if (!summary && !error) {
    return <Typography>Loading...</Typography>;
  }

  const planName = summary?.plan?.plan?.toUpperCase() || 'FREE';
  const jobsRemaining = Math.max((summary?.plan?.max_jobs ?? 0) - (summary?.usage?.total_jobs ?? 0), 0);
  const runsRemainingToday = Math.max(
    (summary?.plan?.max_runs_per_day ?? 0) - (summary?.usage?.runs_today ?? 0),
    0
  );

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h3" gutterBottom>
          Account
        </Typography>
        <Typography color="text.secondary">
          See your current plan, how much you have used, and what your limits mean in everyday terms.
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      {summary && (
        <>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Card sx={{ borderRadius: 4, height: '100%' }}>
                <CardContent>
                  <Typography variant="overline">Plan</Typography>
                  <Typography variant="h4">{planName}</Typography>
                  <Typography color="text.secondary">Your current workspace level</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card sx={{ borderRadius: 4, height: '100%' }}>
                <CardContent>
                  <Typography variant="overline">Jobs Remaining</Typography>
                  <Typography variant="h4">{jobsRemaining}</Typography>
                  <Typography color="text.secondary">More jobs you can still save on this plan</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card sx={{ borderRadius: 4, height: '100%' }}>
                <CardContent>
                  <Typography variant="overline">Runs Left Today</Typography>
                  <Typography variant="h4">{runsRemainingToday}</Typography>
                  <Typography color="text.secondary">Runs still available before the daily limit</Typography>
                </CardContent>
              </Card>
          </Grid>
        </Grid>

          <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card sx={{ borderRadius: 4, height: '100%' }}>
              <CardContent>
                <Stack spacing={1.5}>
                  <Typography variant="overline">Current Plan</Typography>
                  <Typography variant="h4">{planName}</Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    <Chip label={`${summary.plan.max_jobs} max jobs`} size="small" variant="outlined" />
                    <Chip label={`${summary.plan.max_runs_per_day} max runs/day`} size="small" variant="outlined" />
                  </Stack>
                  <Typography color="text.secondary">
                    Your plan decides how many jobs you can save and how many runs you can start each day.
                  </Typography>
                  <Typography>
                    <strong>Max jobs:</strong> {summary.plan.max_jobs}
                  </Typography>
                  <Typography>
                    <strong>Max runs per day:</strong> {summary.plan.max_runs_per_day}
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card sx={{ borderRadius: 4, height: '100%' }}>
              <CardContent>
                <Stack spacing={1.5}>
                  <Typography variant="overline">Usage</Typography>
                  <Typography variant="h5">Your activity so far</Typography>
                  <Typography color="text.secondary">
                    This helps you understand how actively your team is using the workspace.
                  </Typography>
                  <Typography>
                    <strong>Total jobs:</strong> {summary.usage.total_jobs}
                  </Typography>
                  <Typography>
                    <strong>Total runs:</strong> {summary.usage.total_runs}
                  </Typography>
                  <Typography>
                    <strong>Total exports:</strong> {summary.usage.total_exports}
                  </Typography>
                  <Typography>
                    <strong>Runs today:</strong> {summary.usage.runs_today}
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12}>
            <Card sx={{ borderRadius: 4 }}>
              <CardContent>
                <Stack spacing={1}>
                  <Typography variant="h6">What this means</Typography>
                  <Typography color="text.secondary">
                    You are well set up when you still have room for new jobs and enough runs left for today&apos;s work.
                  </Typography>
                  <Typography variant="body2">
                    If you are regularly close to your limits, that is the point where a higher plan becomes useful.
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <WorkspaceHealthCard health={buildWorkspaceHealth({ runs })} />
          </Grid>
          <Grid item xs={12} md={8}>
            <ActivityFeedCard
              items={buildActivityFeed({ jobs, runs, exports })}
              title="Audit And Activity"
              helperText="Track the latest jobs, run outcomes, and exports in one place."
            />
          </Grid>
          </Grid>
        </>
      )}
    </Stack>
  );
};

export default AccountPage;
