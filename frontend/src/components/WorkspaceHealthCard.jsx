import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

const WorkspaceHealthCard = ({ health }) => {
  if (!health) {
    return null;
  }

  return (
    <Card sx={{ borderRadius: 4, height: '100%', bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', color: '#E2E2E3', boxShadow: 'none' }}>
      <CardContent>
        <Stack spacing={2}>
          <div>
            <Typography variant="h6" sx={{ color: '#E2E2E3' }}>Workspace Health</Typography>
            <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
              A quick operational snapshot based on recent run outcomes.
            </Typography>
          </div>

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={health.label} color={health.color} />
            <Chip label={`${health.activeRuns} active runs`} variant="outlined" sx={{ color: '#FFD3A0', borderColor: 'rgba(255, 211, 160, 0.45)' }} />
            <Chip label={`${health.failedRuns} failed runs`} variant="outlined" sx={{ color: '#FFD3A0', borderColor: 'rgba(255, 211, 160, 0.45)' }} />
          </Stack>

          <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
            {health.message}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default WorkspaceHealthCard;
