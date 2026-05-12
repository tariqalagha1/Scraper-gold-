import React from 'react';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

const StructuredPreviewCard = ({ preview, validationErrors, confirmed, onConfirm }) => (
  <Card sx={{ borderRadius: 4, boxShadow: 'none', border: '1px solid rgba(79, 69, 58, 0.5)', bgcolor: 'rgba(28, 31, 35, 0.84)' }}>
    <CardContent>
      <Stack spacing={2}>
        <div>
          <Typography variant="h6" sx={{ color: '#E2E2E3' }}>
            StructuredPreviewCard
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)', mt: 0.5 }}>
            Step 3: Confirm this structured request before running.
          </Typography>
        </div>

        {validationErrors.length > 0 && (
          <Alert severity="error" sx={{ borderRadius: 3 }}>
            {validationErrors.join(' ')}
          </Alert>
        )}

        <Stack
          sx={{
            p: 2,
            borderRadius: 2,
            border: '1px solid rgba(79, 69, 58, 0.5)',
            bgcolor: 'rgba(8, 11, 14, 0.78)',
          }}
          spacing={0.75}
        >
          <Typography variant="subtitle2" sx={{ color: '#F6D28F' }}>
            We will search for:
          </Typography>
          <Typography variant="body2" sx={{ color: '#E2E2E3' }}>
            {preview.query || 'Add what you want to find'}
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.82)', mt: 0.5 }}>
            In {preview.location || 'Add a location'}
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.82)' }}>
            With: {Array.isArray(preview.fields) && preview.fields.length > 0 ? preview.fields.join(', ') : 'Add fields'}
          </Typography>
        </Stack>

        <Button
          type="button"
          variant={confirmed ? 'contained' : 'outlined'}
          onClick={onConfirm}
          disabled={validationErrors.length > 0}
          sx={{
            alignSelf: { xs: 'stretch', sm: 'flex-start' },
            borderRadius: 3,
            textTransform: 'none',
            color: confirmed ? '#121415' : '#FFD3A0',
            borderColor: 'rgba(255, 211, 160, 0.55)',
            background: confirmed ? 'linear-gradient(135deg, #FFD3A0 0%, #E8B678 100%)' : 'transparent',
          }}
        >
          {confirmed ? 'Preview confirmed' : 'Confirm preview'}
        </Button>
      </Stack>
    </CardContent>
  </Card>
);

export default StructuredPreviewCard;
