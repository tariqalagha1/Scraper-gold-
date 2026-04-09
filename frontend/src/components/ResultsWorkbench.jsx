import React, { useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded';
import PreviewRoundedIcon from '@mui/icons-material/PreviewRounded';
import ResultsTable from './ResultsTable';
import {
  buildResultFieldSummary,
  buildResultHighlights,
  buildResultSummary,
} from '../assistant/orchestrator';

const ResultsWorkbench = ({ results }) => {
  const [query, setQuery] = useState('');

  const normalizedResults = useMemo(
    () =>
      (results || []).map((item, index) => ({
        id: item?.id || `result-${index + 1}`,
        data_type: item?.data_type || 'record',
        data_json: item?.data_json && typeof item.data_json === 'object' ? item.data_json : item || {},
      })),
    [results]
  );

  const filteredResults = useMemo(() => {
    if (!query.trim()) return normalizedResults;
    return normalizedResults.filter((item) =>
      JSON.stringify(item.data_json || {}).toLowerCase().includes(query.toLowerCase())
    );
  }, [normalizedResults, query]);

  const previewItem = filteredResults[0] || null;
  const keyFields = buildResultHighlights(filteredResults);
  const summary = buildResultSummary(filteredResults);
  const fieldSummary = buildResultFieldSummary(filteredResults);
  const totalCount = normalizedResults.length || 0;

  return (
    <Stack spacing={2}>
      <Card sx={{ borderRadius: 4, bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', boxShadow: 'none' }}>
        <CardContent>
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} alignItems="center">
              <InsightsRoundedIcon sx={{ color: '#FFD3A0' }} />
              <Typography variant="h6" sx={{ color: '#E2E2E3' }}>Results summary</Typography>
            </Stack>
            <Typography color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>{summary}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
              {fieldSummary}
            </Typography>
            <TextField
              fullWidth
              label="Search results"
              placeholder="Search by name, price, availability..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 3,
                  bgcolor: 'rgba(8, 11, 14, 0.78)',
                  color: '#E2E2E3',
                },
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(79, 69, 58, 0.5)' },
                '& .MuiOutlinedInput-root:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(240, 189, 127, 0.52)' },
                '& .MuiOutlinedInput-root.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#FFD3A0' },
                '& .MuiInputLabel-root': { color: 'rgba(226, 226, 227, 0.72)' },
                '& .MuiInputLabel-root.Mui-focused': { color: '#FFD3A0' },
              }}
            />
            {query.trim() && (
              <Typography variant="body2" color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
                Showing {filteredResults.length} of {totalCount} result{totalCount === 1 ? '' : 's'} for "{query}".
              </Typography>
            )}
          </Stack>
        </CardContent>
      </Card>

      <Grid container spacing={2}>
        <Grid item xs={12} lg={8}>
          <ResultsTable results={filteredResults} />
        </Grid>
        <Grid item xs={12} lg={4}>
          <Card sx={{ borderRadius: 4, bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', boxShadow: 'none' }}>
            <CardContent>
              <Stack spacing={2}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <PreviewRoundedIcon sx={{ color: '#FFD3A0' }} />
                  <Typography variant="h6" sx={{ color: '#E2E2E3' }}>Preview</Typography>
                </Stack>
                {previewItem ? (
                  <>
                    {keyFields.name && <Chip label={`Name: ${keyFields.name}`} sx={{ color: '#E2E2E3', borderColor: 'rgba(79, 69, 58, 0.5)' }} variant="outlined" />}
                    {keyFields.price && <Chip label={`Price: ${keyFields.price}`} sx={{ color: '#30E0A1', borderColor: 'rgba(48,224,161,0.30)' }} variant="outlined" />}
                    {keyFields.availability && <Chip label={`Availability: ${keyFields.availability}`} sx={{ color: '#FFD3A0', borderColor: 'rgba(255, 211, 160, 0.55)' }} variant="outlined" />}
                    <Typography variant="body2" color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
                      This is the first matching item from your current results view.
                    </Typography>
                    <Box
                      sx={{
                        p: 2,
                        borderRadius: 2,
                        bgcolor: 'rgba(8, 11, 14, 0.78)',
                        border: '1px solid rgba(79, 69, 58, 0.5)',
                        maxHeight: 320,
                        overflow: 'auto',
                        color: '#E2E2E3',
                      }}
                    >
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                        {JSON.stringify(previewItem.data_json || {}, null, 2)}
                      </pre>
                    </Box>
                  </>
                ) : (
                  <Typography color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
                    {totalCount === 0
                      ? 'No results are available yet. Once the run finds data, a preview will appear here.'
                      : 'No items match your current search. Try a broader search term.'}
                  </Typography>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Stack>
  );
};


export default ResultsWorkbench;
