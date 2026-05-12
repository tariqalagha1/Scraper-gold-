import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CircularProgress from '@mui/material/CircularProgress';
import LinearProgress from '@mui/material/LinearProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import TaskAltRoundedIcon from '@mui/icons-material/TaskAltRounded';
import RadioButtonUncheckedRoundedIcon from '@mui/icons-material/RadioButtonUncheckedRounded';
import AutorenewRoundedIcon from '@mui/icons-material/AutorenewRounded';

const STEPS = [
  { key: 'searching', label: 'Searching sources' },
  { key: 'extracting', label: 'Extracting records' },
  { key: 'cleaning', label: 'Cleaning results' },
  { key: 'insights', label: 'Generating insights' },
];

const phaseToIndex = (phase) => {
  if (phase === 'preparing') return 0;
  if (phase === 'calling') return 1;
  if (phase === 'processing') return 2;
  if (phase === 'insights') return 3;
  if (phase === 'done') return 3;
  if (phase === 'error') return 3;
  return 0;
};

const TaskProgressPanel = ({ phase, status, onOpenWorkspace }) => {
  const activeIndex = phaseToIndex(phase);
  const isFailed = status === 'failed' || phase === 'error';
  const isDone = phase === 'done' && !isFailed;
  const percent = phase === 'idle' ? 0 : Math.min(100, Math.max(10, ((activeIndex + (isDone ? 1 : 0)) / STEPS.length) * 100));

  return (
    <Card sx={{ borderRadius: 4, bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', boxShadow: 'none' }}>
      <CardContent>
        <Stack spacing={2.25}>
          <div>
            <Typography variant="h6" sx={{ color: '#E2E2E3' }}>
              Working on your search
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)', mt: 0.75 }}>
              We are collecting and preparing your results.
            </Typography>
          </div>

          <Stack direction="row" spacing={1.25} alignItems="center">
            <CircularProgress size={16} thickness={5} sx={{ color: '#FFD3A0' }} />
            <Typography variant="caption" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
              This usually takes a few seconds
            </Typography>
          </Stack>

          <LinearProgress
            variant="determinate"
            value={percent}
            sx={{
              height: 10,
              borderRadius: 999,
              backgroundColor: 'rgba(255,255,255,0.08)',
              '& .MuiLinearProgress-bar': {
                backgroundColor: isFailed ? '#ff6f91' : '#FFD3A0',
              },
            }}
          />

          <Stack spacing={1.25}>
            {STEPS.map((step, index) => {
              const done = isDone || (!isFailed && index < activeIndex);
              const active = !done && index === activeIndex && phase !== 'idle' && !isDone;
              const textColor = done
                ? '#A5E6B8'
                : active
                  ? '#FFD3A0'
                  : 'rgba(226, 226, 227, 0.72)';

              return (
                <Stack key={step.key} direction="row" spacing={1.25} alignItems="center">
                  {done ? (
                    <TaskAltRoundedIcon sx={{ fontSize: 18, color: '#A5E6B8' }} />
                  ) : active ? (
                    <AutorenewRoundedIcon
                      sx={{
                        fontSize: 18,
                        color: isFailed ? '#ff6f91' : '#FFD3A0',
                        animation: 'spin 1s linear infinite',
                        '@keyframes spin': {
                          from: { transform: 'rotate(0deg)' },
                          to: { transform: 'rotate(360deg)' },
                        },
                      }}
                    />
                  ) : (
                    <RadioButtonUncheckedRoundedIcon sx={{ fontSize: 18, color: 'rgba(226, 226, 227, 0.58)' }} />
                  )}
                  <Typography variant="body2" sx={{ color: textColor }}>
                    {step.label}
                  </Typography>
                </Stack>
              );
            })}
          </Stack>
          
          {onOpenWorkspace && (
            <Stack direction="row" justifyContent="flex-end" sx={{ mt: 2 }}>
              <Button
                variant="outlined"
                onClick={onOpenWorkspace}
                sx={{
                  borderRadius: 999,
                  textTransform: 'none',
                  color: '#FFD3A0',
                  borderColor: 'rgba(255, 211, 160, 0.45)',
                }}
              >
                Open Live Workspace
              </Button>
            </Stack>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default TaskProgressPanel;
