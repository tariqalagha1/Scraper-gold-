/**
 * Step-by-step scraping flow wizard component.
 */
import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import Button from '@mui/material/Button';

const steps = ['Enter URL', 'Select Data Type', 'Configure Options', 'Review & Submit'];
const warmGold = '#E2BC8B';
const warmGoldStrong = '#FFD3A0';
const warmBorder = 'rgba(110, 92, 73, 0.78)';
const panelBackground = 'rgba(8, 11, 14, 0.62)';

const StepWizard = ({
  children,
  onSubmit,
  submitLabel = 'Submit',
  submittingLabel = null,
  isSubmitting = false,
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const isFinalStep = activeStep === steps.length - 1;
  const finalStepLabel = isSubmitting && submittingLabel ? submittingLabel : submitLabel;

  const handleNext = () => {
    if (isFinalStep) {
      onSubmit();
    } else {
      setActiveStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Stepper
        activeStep={activeStep}
        sx={{
          '& .MuiStepLabel-label': {
            color: 'rgba(226,226,227,0.72)',
            fontWeight: 600,
            letterSpacing: '0.03em',
          },
          '& .MuiStepLabel-label.Mui-active': {
            color: warmGoldStrong,
          },
          '& .MuiStepLabel-label.Mui-completed': {
            color: warmGold,
          },
          '& .MuiStepIcon-root': {
            color: 'rgba(45, 42, 37, 0.9)',
            border: `1px solid ${warmBorder}`,
            borderRadius: '999px',
          },
          '& .MuiStepIcon-root.Mui-active': {
            color: warmGold,
            boxShadow: '0 0 0 3px rgba(226, 188, 139, 0.18)',
          },
          '& .MuiStepIcon-root.Mui-completed': {
            color: '#C99A60',
          },
          '& .MuiStepConnector-line': {
            borderColor: warmBorder,
            borderTopWidth: 2,
          },
        }}
      >
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      <Box
        sx={{
          mt: 4,
          mb: 4,
          p: 2.25,
          borderRadius: 2,
          border: `1px solid ${warmBorder}`,
          background: panelBackground,
        }}
      >
        {React.Children.toArray(children)[activeStep]}
      </Box>
      <Box sx={{ display: 'flex', flexDirection: 'row', pt: 2 }}>
        <Button
          color="inherit"
          disabled={activeStep === 0}
          onClick={handleBack}
          sx={{
            mr: 1,
            border: `1px solid ${warmBorder}`,
            borderRadius: 2,
            px: 2,
            color: '#E2E2E3',
            backgroundColor: 'rgba(13,16,20,0.6)',
            '&:hover': {
              borderColor: warmGold,
              backgroundColor: 'rgba(24,28,33,0.75)',
            },
            '&.Mui-disabled': {
              color: 'rgba(226,226,227,0.38)',
              borderColor: 'rgba(110, 92, 73, 0.3)',
            },
          }}
        >
          Back
        </Button>
        <Box sx={{ flex: '1 1 auto' }} />
        <Button
          onClick={handleNext}
          variant="contained"
          sx={{
            borderRadius: 2,
            px: 2.5,
            background: 'linear-gradient(135deg, #FFD3A0 0%, #E2BC8B 52%, #C99A60 100%)',
            color: '#121315',
            fontWeight: 700,
            letterSpacing: '0.04em',
            boxShadow: '0 8px 22px rgba(201, 154, 96, 0.34)',
            '&:hover': {
              background: 'linear-gradient(135deg, #FFE1BD 0%, #EBC692 52%, #D0A56E 100%)',
            },
          }}
        >
          {isFinalStep ? finalStepLabel : 'Next'}
        </Button>
      </Box>
    </Box>
  );
};

export default StepWizard;
