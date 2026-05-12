import React from 'react';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import LightbulbRoundedIcon from '@mui/icons-material/LightbulbRounded';

const InsightResultPanel = ({ summaryMetrics, insights }) => {
  if (!summaryMetrics) {
    return null;
  }

  return (
    <Card sx={{ borderRadius: 4, boxShadow: 'none', border: '1px solid rgba(79, 69, 58, 0.5)', bgcolor: 'rgba(28, 31, 35, 0.84)' }}>
      <CardContent>
        <Stack spacing={2.25}>
          <Stack direction="row" spacing={1} alignItems="center">
            <LightbulbRoundedIcon sx={{ color: '#FFD3A0' }} />
            <Typography variant="h6" sx={{ color: '#E2E2E3' }}>
              Your answer
            </Typography>
          </Stack>

          <Box
            sx={{
              borderRadius: 3,
              border: '1px solid rgba(255, 211, 160, 0.35)',
              background: 'linear-gradient(135deg, rgba(255, 211, 160, 0.13) 0%, rgba(232, 182, 120, 0.06) 100%)',
              p: 2.2,
            }}
            data-testid="first-success-summary-card"
          >
            <Typography variant="subtitle2" sx={{ color: '#F6D28F', mb: 0.75 }}>
              Summary
            </Typography>
            <Typography variant="h6" sx={{ color: '#EDE6DE', lineHeight: 1.4 }}>
              {insights.summary}
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
              <Chip label={`Total: ${summaryMetrics.total}`} variant="outlined" sx={{ color: '#E2E2E3' }} />
              <Chip label={`Coverage: ${Math.round((summaryMetrics.coverage || 0) * 100)}%`} variant="outlined" sx={{ color: '#E2E2E3' }} />
              <Chip label={`Confidence: ${Math.round((summaryMetrics.confidence || 0) * 100)}%`} variant="outlined" sx={{ color: '#E2E2E3' }} />
              <Chip label={`Status: ${summaryMetrics.status || 'unknown'}`} variant="outlined" sx={{ color: '#E2E2E3' }} />
            </Stack>
          </Box>

          <div>
            <Typography variant="subtitle2" sx={{ color: '#F6D28F', mb: 0.75 }}>
              Key findings
            </Typography>
            <Stack spacing={0.75}>
              {insights.key_findings.map((finding) => (
                <Typography key={finding} variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.78)' }}>
                  {finding}
                </Typography>
              ))}
            </Stack>
          </div>

          <div>
            <Typography variant="subtitle2" sx={{ color: '#F6D28F', mb: 0.5 }}>
              Data quality note
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.78)' }}>
              {insights.data_quality_note}
            </Typography>
          </div>

          <div>
            <Typography variant="subtitle2" sx={{ color: '#F6D28F', mb: 0.5 }}>
              Recommended next step
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.78)' }}>
              {insights.recommended_next_step}
            </Typography>
          </div>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default InsightResultPanel;
