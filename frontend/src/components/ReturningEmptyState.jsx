import React from 'react';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

const EXAMPLE_PROMPTS = [
  'Hospitals in Riyadh',
  'Clinics in Jeddah',
  'Companies in Saudi Arabia',
];

const ReturningEmptyState = ({ onUseSample, onUseTemplate }) => (
  <Card
    sx={{
      borderRadius: 4,
      boxShadow: 'none',
      border: '1px solid rgba(79, 69, 58, 0.5)',
      bgcolor: 'rgba(28, 31, 35, 0.84)',
    }}
  >
    <CardContent>
      <Stack spacing={2}>
        <div>
          <Typography variant="h6" sx={{ color: '#E2E2E3' }}>
            What do you want to find today?
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)', mt: 0.5 }}>
            Start with a quick idea or choose a sample to begin.
          </Typography>
        </div>

        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {EXAMPLE_PROMPTS.map((prompt) => (
            <Chip
              key={prompt}
              label={prompt}
              clickable
              onClick={() => onUseSample(prompt)}
              variant="outlined"
              sx={{
                color: '#E2E2E3',
                borderColor: 'rgba(255, 211, 160, 0.45)',
                background: 'rgba(255, 255, 255, 0.03)',
              }}
            />
          ))}
        </Stack>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Button
            type="button"
            variant="contained"
            onClick={() => onUseSample(EXAMPLE_PROMPTS[0])}
            sx={{
              borderRadius: 3,
              textTransform: 'none',
              background: 'linear-gradient(135deg, #FFD3A0 0%, #E8B678 100%)',
              color: '#121415',
            }}
          >
            Use a sample
          </Button>
          <Button
            type="button"
            variant="outlined"
            onClick={onUseTemplate}
            sx={{
              borderRadius: 3,
              textTransform: 'none',
              color: '#E2E2E3',
              borderColor: 'rgba(226, 226, 227, 0.32)',
            }}
          >
            Start with a template
          </Button>
        </Stack>
      </Stack>
    </CardContent>
  </Card>
);

export default ReturningEmptyState;
