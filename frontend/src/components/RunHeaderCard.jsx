import React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { formatDate, formatStatus, getStatusColor } from '../utils/helpers';

const RunHeaderCard = ({
  job,
  latestRun,
  activeRun,
  startingRun,
  retryingRun,
  onStartRun,
  onRetryRun,
}) => (
  <Card sx={{ borderRadius: 4, overflow: 'hidden' }}>
    <CardContent>
      <Stack spacing={2}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: 2,
            alignItems: 'flex-start',
            flexWrap: 'wrap',
          }}
        >
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography variant="h4" sx={{ overflowWrap: 'anywhere' }}>{job.url}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              This workspace shows your latest run, explains what happened, and keeps everything in one place.
            </Typography>
            <Box sx={{ mt: 1.5, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Chip label={job.scrape_type} />
              <Chip label={formatStatus(job.status)} color={getStatusColor(job.status)} />
              {latestRun && (
                <Chip
                  label={`${formatStatus(latestRun.status)} ${latestRun.progress ?? 0}%`}
                  color={getStatusColor(latestRun.status)}
                />
              )}
            </Box>
          </Box>

          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', width: { xs: '100%', sm: 'auto' } }}>
            <Button variant="contained" onClick={onStartRun} disabled={startingRun || Boolean(activeRun)}>
              {startingRun ? 'Starting...' : 'Start Run'}
            </Button>
            <Button
              variant="outlined"
              onClick={onRetryRun}
              disabled={retryingRun || !latestRun || latestRun.status !== 'failed' || Boolean(activeRun)}
            >
              {retryingRun ? 'Retrying...' : 'Try Again'}
            </Button>
          </Box>
        </Box>

        {latestRun && (
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <Typography variant="body2">
              <strong>Started:</strong> {formatDate(latestRun.started_at)}
            </Typography>
            <Typography variant="body2">
              <strong>Finished:</strong> {formatDate(latestRun.finished_at)}
            </Typography>
          </Stack>
        )}
      </Stack>
    </CardContent>
  </Card>
);

export default RunHeaderCard;
