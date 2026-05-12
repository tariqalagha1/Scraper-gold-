import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import ResultsTable from './ResultsTable';

const ResultTablePanel = ({ data }) => {
  const normalized = Array.isArray(data)
    ? data.map((item, index) => ({
        id: `record-${index + 1}`,
        data_type: 'record',
        data_json: item && typeof item === 'object' ? item : {},
      }))
    : [];

  return (
    <Card sx={{ borderRadius: 4, boxShadow: 'none', border: '1px solid rgba(79, 69, 58, 0.5)', bgcolor: 'rgba(28, 31, 35, 0.84)' }}>
      <CardContent>
        <Stack spacing={2}>
          <div>
            <Typography variant="h6" sx={{ color: '#E2E2E3' }}>
              Result table
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)', mt: 0.5 }}>
              Detailed records from your search.
            </Typography>
          </div>
          <ResultsTable results={normalized} />
        </Stack>
      </CardContent>
    </Card>
  );
};

export default ResultTablePanel;
