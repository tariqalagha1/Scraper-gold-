import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import LinearProgress from '@mui/material/LinearProgress';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { buildRunStatusMessage, humanizeLog } from '../assistant/orchestrator';
import { formatDate, formatStatus } from '../utils/helpers';

const RunProgressCard = ({ run, logs = [] }) => {
  if (!run) {
    return null;
  }

  return (
    <Card sx={{ borderRadius: 4 }}>
      <CardContent>
        <Stack spacing={2}>
          <Typography variant="h6">Live Progress</Typography>
          <Typography>
            <strong>Status:</strong> {formatStatus(run.status)}
          </Typography>
          <Typography>
            <strong>Progress:</strong> {run.progress ?? 0}%
          </Typography>
          <LinearProgress
            variant="determinate"
            value={run.progress ?? 0}
            sx={{ height: 10, borderRadius: 999 }}
          />
          <Typography color="text.secondary">{buildRunStatusMessage(run)}</Typography>
          <Typography variant="body2" color="text.secondary">
            Started {formatDate(run.started_at)}{run.finished_at ? ` and finished ${formatDate(run.finished_at)}` : ''}.
          </Typography>

          <Stack spacing={1}>
            <Typography variant="subtitle2">What the assistant is doing</Typography>
            {logs.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                We will show clear step-by-step updates here as soon as the website starts responding.
              </Typography>
            ) : (
              <List disablePadding>
                {logs.slice(-5).map((entry, index) => (
                  <ListItem key={`${entry.timestamp}-${entry.event}-${index}`} divider>
                    <ListItemText
                      primary={humanizeLog(entry)}
                      secondary={formatDate(entry.timestamp)}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default RunProgressCard;
