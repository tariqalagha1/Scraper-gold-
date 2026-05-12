import React, { useMemo } from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import LinearProgress from '@mui/material/LinearProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import TaskAltRoundedIcon from '@mui/icons-material/TaskAltRounded';
import RadioButtonUncheckedRoundedIcon from '@mui/icons-material/RadioButtonUncheckedRounded';
import AutorenewRoundedIcon from '@mui/icons-material/AutorenewRounded';

const PROGRESS_STEPS = [
  { key: 'understanding', title: 'Understanding your request' },
  { key: 'visiting', title: 'Visiting website pages' },
  { key: 'collecting', title: 'Collecting useful details' },
  { key: 'preparing', title: 'Preparing your results' },
];

const getActiveStepIndex = (run) => {
  if (!run) return 0;

  const status = String(run.status || '').toLowerCase();
  const progress = Number(run.progress || 0);

  if (status === 'completed') return PROGRESS_STEPS.length - 1;
  if (status === 'failed') {
    if (progress >= 85) return 3;
    if (progress >= 55) return 2;
    if (progress >= 25) return 1;
    return 0;
  }
  if (progress >= 85) return 3;
  if (progress >= 55) return 2;
  if (progress >= 25) return 1;
  return 0;
};

const getHeadline = (run) => {
  if (!run) {
    return 'Ready whenever you are.';
  }
  const status = String(run.status || '').toLowerCase();
  if (status === 'completed') {
    return 'Done. Your results are ready.';
  }
  if (status === 'failed') {
    return 'This run stopped early. You can retry in one click.';
  }
  if (status === 'pending') {
    return 'Queued and starting shortly.';
  }
  return 'Working on your request now.';
};

const SimpleProgressJourney = ({ run }) => {
  const activeIndex = useMemo(() => getActiveStepIndex(run), [run]);
  const percent = Number(run?.progress || 0);
  const status = String(run?.status || '').toLowerCase();
  const hasFailed = status === 'failed';
  const isCompleted = status === 'completed';

  return (
    <Card sx={{ borderRadius: 4, bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', boxShadow: 'none' }}>
      <CardContent>
        <Stack spacing={2.25}>
          <div>
            <Typography variant="h6" sx={{ color: '#E2E2E3' }}>
              Progress
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)', mt: 0.75 }}>
              {getHeadline(run)}
            </Typography>
          </div>

          <LinearProgress
            variant="determinate"
            value={Math.max(0, Math.min(100, percent))}
            sx={{
              height: 10,
              borderRadius: 999,
              backgroundColor: 'rgba(255,255,255,0.08)',
              '& .MuiLinearProgress-bar': {
                backgroundColor: hasFailed ? '#ff6f91' : '#FFD3A0',
              },
            }}
          />

          <Stack spacing={1.25}>
            {PROGRESS_STEPS.map((step, index) => {
              const isDone = isCompleted || (!hasFailed && index < activeIndex);
              const isActive = !isDone && index === activeIndex;
              const textColor = isDone
                ? '#A5E6B8'
                : isActive
                  ? '#FFD3A0'
                  : 'rgba(226, 226, 227, 0.72)';

              return (
                <Stack key={step.key} direction="row" spacing={1.25} alignItems="center">
                  {isDone ? (
                    <TaskAltRoundedIcon sx={{ fontSize: 18, color: '#A5E6B8' }} />
                  ) : isActive ? (
                    <AutorenewRoundedIcon sx={{ fontSize: 18, color: hasFailed ? '#ff6f91' : '#FFD3A0' }} />
                  ) : (
                    <RadioButtonUncheckedRoundedIcon sx={{ fontSize: 18, color: 'rgba(226, 226, 227, 0.58)' }} />
                  )}
                  <Typography variant="body2" sx={{ color: textColor }}>
                    {step.title}
                  </Typography>
                </Stack>
              );
            })}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default SimpleProgressJourney;
