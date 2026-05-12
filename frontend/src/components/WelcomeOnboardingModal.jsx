import React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';

const SAMPLE_CHIPS = [
  'Hospitals in Riyadh with emails',
  'Clinics in Jeddah',
  'Companies in Saudi Arabia',
];

const WelcomeOnboardingModal = ({ open, onTrySample, onSkip, onClose, onSelectSample }) => (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="sm"
      aria-labelledby="welcome-onboarding-title"
      PaperProps={{
        sx: {
          borderRadius: 4,
          border: '1px solid rgba(79, 69, 58, 0.5)',
          background: 'linear-gradient(160deg, rgba(30, 33, 37, 0.96) 0%, rgba(16, 19, 24, 0.98) 100%)',
        },
      }}
    >
      <DialogTitle
        id="welcome-onboarding-title"
        sx={{
          color: '#E2E2E3',
          pr: 7,
          fontWeight: 700,
        }}
      >
        Find data instantly — no setup needed
        <IconButton
          aria-label="Close welcome modal"
          onClick={onClose}
          sx={{
            position: 'absolute',
            right: 12,
            top: 12,
            color: 'rgba(226, 226, 227, 0.72)',
          }}
        >
          <CloseRoundedIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent>
        <Typography sx={{ color: 'rgba(226, 226, 227, 0.76)', mb: 2.5 }}>
          Describe what you need, and we’ll help structure it automatically.
        </Typography>

        <Box>
          <Typography variant="caption" sx={{ color: '#F6D28F', display: 'block', mb: 1 }}>
            Try a quick example
          </Typography>
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
            {SAMPLE_CHIPS.map((sample) => (
              <Chip
                key={sample}
                label={sample}
                clickable
                onClick={() => onSelectSample(sample)}
                sx={{
                  color: '#E2E2E3',
                  borderColor: 'rgba(255, 211, 160, 0.45)',
                  background: 'rgba(255, 255, 255, 0.03)',
                }}
                variant="outlined"
              />
            ))}
          </Stack>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button
          variant="outlined"
          onClick={onSkip}
          sx={{
            borderRadius: 3,
            textTransform: 'none',
            color: '#E2E2E3',
            borderColor: 'rgba(226, 226, 227, 0.25)',
          }}
        >
          Skip
        </Button>
        <Button
          variant="contained"
          onClick={onTrySample}
          sx={{
            borderRadius: 3,
            textTransform: 'none',
            background: 'linear-gradient(135deg, #FFD3A0 0%, #E8B678 100%)',
            color: '#121415',
          }}
        >
          Try a sample search
        </Button>
      </DialogActions>
    </Dialog>
  );

export default WelcomeOnboardingModal;
