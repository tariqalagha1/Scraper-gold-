/**
 * Data type selector component.
 * Allows user to select: general, pdf, word, excel, images, videos, structured
 */
import React from 'react';
import Box from '@mui/material/Box';
import FormControl from '@mui/material/FormControl';
import FormLabel from '@mui/material/FormLabel';
import RadioGroup from '@mui/material/RadioGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import Radio from '@mui/material/Radio';
import Typography from '@mui/material/Typography';

const dataTypes = [
  { value: 'general', label: 'General', description: 'Extract general web content' },
  { value: 'pdf', label: 'PDF Documents', description: 'Extract and download PDF files' },
  { value: 'word', label: 'Word Documents', description: 'Extract and download Word files' },
  { value: 'excel', label: 'Excel Files', description: 'Download existing .xls/.xlsx/.csv files linked on the page' },
  { value: 'images', label: 'Images', description: 'Extract and download images' },
  { value: 'videos', label: 'Videos', description: 'Extract and download videos' },
  { value: 'structured', label: 'Structured Data', description: 'Extract table rows and structured fields (name, ID, phone, etc.)' },
];
const warmGold = '#E2BC8B';
const warmGoldStrong = '#FFD3A0';
const warmBorder = 'rgba(110, 92, 73, 0.78)';
const optionBackground = 'rgba(8, 11, 14, 0.62)';
const selectedBackground = 'rgba(28, 22, 14, 0.45)';

const DataTypeSelector = ({ value, onChange }) => {
  return (
    <FormControl component="fieldset" sx={{ width: '100%' }}>
      <FormLabel
        component="legend"
        sx={{
          color: '#E2E2E3',
          fontWeight: 600,
          letterSpacing: '0.02em',
          mb: 1.5,
          '&.Mui-focused': {
            color: warmGoldStrong,
          },
        }}
      >
        Select Data Type to Extract
      </FormLabel>
      <RadioGroup value={value} onChange={(e) => onChange(e.target.value)} sx={{ gap: 1.1 }}>
        {dataTypes.map((type) => (
          <Box
            key={type.value}
            sx={{
              px: 1.2,
              py: 0.7,
              borderRadius: 1.8,
              border: `1.5px solid ${value === type.value ? warmGold : warmBorder}`,
              backgroundColor: value === type.value ? selectedBackground : optionBackground,
              boxShadow: value === type.value ? '0 0 0 2px rgba(226, 188, 139, 0.16)' : 'none',
            }}
          >
            <FormControlLabel
              value={type.value}
              control={(
                <Radio
                  sx={{
                    color: '#9E8A73',
                    '&.Mui-checked': {
                      color: warmGoldStrong,
                    },
                  }}
                />
              )}
              sx={{ m: 0, alignItems: 'flex-start' }}
              label={
                <Box>
                  <Typography
                    variant="body1"
                    sx={{
                      color: '#E2E2E3',
                      fontWeight: value === type.value ? 700 : 500,
                    }}
                  >
                    {type.label}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{ color: value === type.value ? warmGold : 'rgba(226,226,227,0.72)' }}
                  >
                    {type.description}
                  </Typography>
                </Box>
              }
            />
          </Box>
        ))}
      </RadioGroup>
    </FormControl>
  );
};

export default DataTypeSelector;
