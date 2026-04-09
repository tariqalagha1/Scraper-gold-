import React, { useMemo } from 'react';
import Alert from '@mui/material/Alert';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { buildRunExplanation } from '../assistant/orchestrator';

const AIExplanationCard = ({ run, results, logs = [] }) => {
  const summary = useMemo(() => buildRunExplanation({ run, results, logs }), [run, results, logs]);

  return (
    <Card sx={{ borderRadius: 4 }}>
      <CardContent>
        <Stack spacing={2}>
          <Typography variant="h6">{summary.title}</Typography>
          <Typography variant="body2" color="text.secondary">
            Here is the plain-language summary of this run.
          </Typography>
          <Alert severity={summary.severity}>
            <strong>What happened:</strong> {summary.whatHappened}
          </Alert>
          <Typography><strong>What was found:</strong> {summary.whatWasFound}</Typography>
          <Typography><strong>What it means:</strong> {summary.whatItMeans}</Typography>
          <Typography><strong>What to do next:</strong> {summary.nextStep}</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {summary.suggestions.map((item) => (
              <Chip key={item} label={item} variant="outlined" />
            ))}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
};


export default AIExplanationCard;
