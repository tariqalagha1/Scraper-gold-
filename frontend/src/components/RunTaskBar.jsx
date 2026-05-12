import React from 'react';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded';

const RunTaskBar = ({ canRun, isRunning, searchSummary, onRun }) => (
  <Card sx={{ borderRadius: 4, boxShadow: 'none', border: '1px solid rgba(79, 69, 58, 0.5)', bgcolor: 'rgba(28, 31, 35, 0.84)' }}>
    <CardContent>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }} justifyContent="space-between">
        <div>
          <Typography variant="h6" sx={{ color: '#E2E2E3' }}>
            Ready to run
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)', mt: 0.5 }}>
            {searchSummary}
          </Typography>
          <Typography variant="caption" sx={{ color: '#F6D28F' }}>
            This usually takes a few seconds
          </Typography>
        </div>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Button
            type="button"
            variant="contained"
            onClick={onRun}
            disabled={!canRun || isRunning}
            startIcon={<PlayArrowRoundedIcon />}
            sx={{
              borderRadius: 3,
              px: 3,
              background: 'linear-gradient(135deg, #FFD3A0 0%, #E8B678 100%)',
              color: '#121415',
              textTransform: 'none',
            }}
          >
            {isRunning ? 'Running...' : 'Run Search'}
          </Button>
        </Stack>
      </Stack>
    </CardContent>
  </Card>
);

export default RunTaskBar;
