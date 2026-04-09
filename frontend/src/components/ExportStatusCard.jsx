import React from 'react';
import Alert from '@mui/material/Alert';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import ExportButton from './ExportButton';
import { formatFileSize } from '../utils/helpers';

const ExportStatusCard = ({ run, exportMessage, exportMeta = null, onExport }) => (
  <Card sx={{ borderRadius: 4 }}>
    <CardContent>
      <Stack spacing={2}>
        <Typography variant="h6">Export</Typography>
        <Typography variant="body2" color="text.secondary">
          When your run is complete, you can export the results in the format that works best for you.
        </Typography>

        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip
            label={
              run?.status === 'completed'
                ? 'Ready to export'
                : 'Available after the run completes'
            }
            color={run?.status === 'completed' ? 'success' : 'default'}
            variant="outlined"
          />
          {run?.id && <Chip label={`Run ${run.id}`} variant="outlined" />}
        </Stack>

        <ExportButton
          runId={run?.id || null}
          onExport={onExport}
          disabled={!run || run.status !== 'completed'}
        />

        {!run && (
          <Typography variant="body2" color="text.secondary">
            Start a run first, then come back here when the results are ready.
          </Typography>
        )}

        {run && run.status !== 'completed' && (
          <Typography variant="body2" color="text.secondary">
            Exports become available as soon as this run finishes successfully.
          </Typography>
        )}

        {exportMessage && <Alert severity="success">{exportMessage}</Alert>}

        {exportMeta && (
          <Alert severity="info">
            {exportMeta.file_name ? `File: ${exportMeta.file_name}. ` : ''}
            {exportMeta.file_size ? `Size: ${formatFileSize(exportMeta.file_size)}.` : 'Size will appear when the file is ready.'}
          </Alert>
        )}
      </Stack>
    </CardContent>
  </Card>
);

export default ExportStatusCard;
