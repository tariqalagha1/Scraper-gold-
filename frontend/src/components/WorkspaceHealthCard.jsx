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
    <Card sx={{ borderRadius: 4, height: '100%' }}>
      <CardContent>
        <Stack spacing={2}>
          <div>
            <Typography variant="h6">Workspace Health</Typography>
            <Typography variant="body2" color="text.secondary">
              A quick operational snapshot based on recent run outcomes.
            </Typography>
          </div>

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={health.label} color={health.color} />
            <Chip label={`${health.activeRuns} active runs`} variant="outlined" />
            <Chip label={`${health.failedRuns} failed runs`} variant="outlined" />
          </Stack>

          <Typography variant="body2" color="text.secondary">
            {health.message}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default WorkspaceHealthCard;
