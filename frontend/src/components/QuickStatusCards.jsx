import React from 'react';
import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import AutoGraphRoundedIcon from '@mui/icons-material/AutoGraphRounded';
import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined';
import PlayCircleOutlineRoundedIcon from '@mui/icons-material/PlayCircleOutlineRounded';
import WorkspacePremiumRoundedIcon from '@mui/icons-material/WorkspacePremiumRounded';

const toCompressionPercentage = (ratio) => {
  const normalizedRatio = Number(ratio);
  if (!Number.isFinite(normalizedRatio)) {
    return null;
  }

  const boundedRatio = Math.min(1, Math.max(0, normalizedRatio));
  return Math.round((1 - boundedRatio) * 100);
};

const QuickStatusCards = ({ jobs = [], runs = [], accountSummary = null }) => {
  const completedRuns = runs.filter((run) => run.status === 'completed').length;
  const failedRuns = runs.filter((run) => run.status === 'failed').length;
  const recentSignal = failedRuns > 0 && failedRuns >= completedRuns ? 'Needs attention' : 'Healthy';
  const latestTelemetryRun = [...runs]
    .sort((left, right) => {
      const leftTimestamp = new Date(left.finished_at || left.started_at || left.created_at || 0).getTime();
      const rightTimestamp = new Date(right.finished_at || right.started_at || right.created_at || 0).getTime();
      return rightTimestamp - leftTimestamp;
    })
    .find((run) => toCompressionPercentage(run.token_compression_ratio) !== null);
  const compressionPercent = latestTelemetryRun
    ? toCompressionPercentage(latestTelemetryRun.token_compression_ratio)
    : null;
  const runSignalLabel = compressionPercent !== null
    ? `Compressed: ${compressionPercent}%`
    : recentSignal;
  const runSignalColor = compressionPercent !== null
    ? 'info'
    : (recentSignal === 'Healthy' ? 'success' : 'warning');
  const runSignalHelp = compressionPercent !== null
    ? `${completedRuns} completed, ${failedRuns} failed`
    : `${completedRuns} completed, ${failedRuns} failed`;

  const cards = [
    {
      label: 'Total Jobs',
      value: jobs.length,
      help: 'Saved scraping jobs in your workspace',
      icon: <Inventory2OutlinedIcon sx={{ color: '#FFD3A0' }} />,
    },
    {
      label: 'Total Runs',
      value: accountSummary?.usage?.total_runs ?? runs.length,
      help: 'Run attempts started from your jobs',
      icon: <PlayCircleOutlineRoundedIcon sx={{ color: '#FFD3A0' }} />,
    },
    {
      label: 'Plan',
      value: accountSummary?.plan?.plan?.toUpperCase() || 'FREE',
      help: 'Current workspace subscription',
      icon: <WorkspacePremiumRoundedIcon sx={{ color: '#FFD3A0' }} />,
    },
    {
      label: 'Run Health',
      value: runSignalLabel,
      help: runSignalHelp,
      icon: <AutoGraphRoundedIcon sx={{ color: '#FFD3A0' }} />,
    },
  ];

  return (
    <Grid container spacing={2}>
      {cards.map((card) => (
        <Grid item xs={12} sm={6} lg={3} key={card.label}>
          <Card sx={{ borderRadius: 4, height: '100%', bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', boxShadow: 'none' }}>
            <CardContent>
              {card.icon}
              <Typography variant="overline" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>{card.label}</Typography>
              <Typography variant="h5" sx={{ mt: 0.5, color: '#E2E2E3' }}>
                {card.value}
              </Typography>
              {card.label === 'Run Health' && (
                <Chip
                  label={card.value}
                  size="small"
                  color={runSignalColor}
                  sx={{
                    mt: 1,
                    borderColor: compressionPercent !== null ? 'rgba(240, 189, 127, 0.52)' : undefined,
                    color: compressionPercent !== null ? '#F0BD7F' : undefined,
                    backgroundColor: compressionPercent !== null ? 'rgba(240, 189, 127, 0.08)' : undefined,
                  }}
                />
              )}
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, color: 'rgba(226, 226, 227, 0.72)' }}>
                {card.help}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

export default QuickStatusCards;
