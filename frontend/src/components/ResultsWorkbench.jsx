import React, { useMemo, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
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

const parseNumericValue = (value) => {
  if (typeof value === 'number') return value;
  const match = String(value || '').match(/(\d+(\.\d+)?)/);
  return match ? Number(match[1]) : null;
};

const extractRows = (results = []) => {
  if (!Array.isArray(results)) return [];
  const rows = [];

  results.forEach((entry) => {
    if (!entry || typeof entry !== 'object') return;
    const payload = entry?.data_json && typeof entry.data_json === 'object' ? entry.data_json : entry;
    if (!payload || typeof payload !== 'object') return;

    if (Array.isArray(payload.items) && payload.items.length > 0) {
      payload.items.forEach((item) => {
        if (item && typeof item === 'object') rows.push(item);
      });
      return;
    }
    if (Array.isArray(payload.result?.data) && payload.result.data.length > 0) {
      payload.result.data.forEach((item) => {
        if (item && typeof item === 'object') rows.push(item);
      });
      return;
    }
    if (Array.isArray(payload.data) && payload.data.length > 0) {
      payload.data.forEach((item) => {
        if (item && typeof item === 'object') rows.push(item);
      });
      return;
    }

    const isFailedEnvelope = String(payload.status || '').toLowerCase() === 'failed';
    if (!isFailedEnvelope) {
      rows.push(payload);
    }
  });

  return rows;
};

const ResultsWorkbench = ({
  results,
  onStartNewRequest,
  onOpenExports,
  onOpenWorkspace,
  advancedView = false,
}) => {
  const [query, setQuery] = useState('');

  const structuredRows = useMemo(() => extractRows(results), [results]);

  const filteredRows = useMemo(() => {
    if (!query.trim()) return structuredRows;
    return structuredRows.filter((item) =>
      JSON.stringify(item || {}).toLowerCase().includes(query.toLowerCase())
    );
  }, [structuredRows, query]);

  const totalCount = structuredRows.length || 0;
  const previewItem = filteredRows[0] || null;
  const keyFields = buildResultHighlights(filteredRows);
  const summary = buildResultSummary(filteredRows);
  const fieldSummary = buildResultFieldSummary(filteredRows);
  const latestPayload = useMemo(() => {
    const first = results?.[0];
    return first?.data_json && typeof first.data_json === 'object' ? first.data_json : {};
  }, [results]);

  const outputMonitoring = useMemo(() => {
    const payloadSummary = String(latestPayload?.summary || latestPayload?.insights?.summary || '').trim();
    const validation = latestPayload?.execution?.validation || {};
    const confidence = Number(validation?.confidence);
    const fillRatio = Number(validation?.metrics?.fill_ratio);
    const sourceCount = Array.isArray(latestPayload?.result?.data)
      ? latestPayload.result.data.length
      : Array.isArray(latestPayload?.links)
        ? latestPayload.links.length
        : totalCount;
    const errors = Array.isArray(latestPayload?.errors) ? latestPayload.errors : [];
    const warnings = Array.isArray(validation?.issues) ? validation.issues : [];

    return {
      summaryText: payloadSummary || summary,
      sourceCount,
      confidence: Number.isFinite(confidence) ? confidence : null,
      quality: Number.isFinite(fillRatio) ? fillRatio : null,
      issues: [...errors, ...warnings].filter((item) => String(item || '').trim()),
    };
  }, [latestPayload, summary, totalCount]);

  const insightItems = useMemo(() => {
    if (!filteredRows.length) {
      return [];
    }

    const priceValues = filteredRows
      .map((item) => parseNumericValue(item?.price || item?.amount))
      .filter((item) => Number.isFinite(item));

    const availableCount = filteredRows.filter((item) => {
      const value = String(item?.availability || item?.stock || '').toLowerCase();
      return value.includes('in stock') || value.includes('available') || value.includes('yes');
    }).length;

    const items = [
      `Summary: ${summary}`,
      fieldSummary,
    ];

    if (priceValues.length > 0) {
      const min = Math.min(...priceValues);
      const max = Math.max(...priceValues);
      items.push(`Price range seen: ${min} to ${max}.`);
    }

    if (availableCount > 0) {
      items.push(`${availableCount} item${availableCount === 1 ? '' : 's'} currently look available.`);
    }

    return items.slice(0, 4);
  }, [fieldSummary, filteredRows, summary]);

  const showActions = Boolean(onOpenExports || onOpenWorkspace || onStartNewRequest);

  if (totalCount === 0) {
    return (
      <Card sx={{ borderRadius: 4, bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', boxShadow: 'none' }}>
        <CardContent>
          <Stack spacing={2}>
            <Typography variant="h6" sx={{ color: '#E2E2E3' }}>No results yet</Typography>
            <Typography sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
              Run a request and your results will appear here in a simple, readable format.
            </Typography>
            <Box sx={{ p: 2, borderRadius: 2, border: '1px solid rgba(79, 69, 58, 0.5)', bgcolor: 'rgba(8, 11, 14, 0.78)' }}>
              <Typography variant="subtitle2" sx={{ color: '#FFD3A0', mb: 1 }}>Try requests like:</Typography>
              <Stack spacing={0.75}>
                <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.74)' }}>
                  Find product names, prices, and stock status.
                </Typography>
                <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.74)' }}>
                  Collect event titles, dates, and signup links.
                </Typography>
                <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.74)' }}>
                  Gather contact names, emails, and phone numbers.
                </Typography>
              </Stack>
            </Box>
            {showActions && (
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                {onStartNewRequest && (
                  <Button variant="contained" onClick={onStartNewRequest}>
                    Start a request
                  </Button>
                )}
                {onOpenWorkspace && (
                  <Button variant="outlined" onClick={onOpenWorkspace}>
                    Open workspace
                  </Button>
                )}
              </Stack>
            )}
          </Stack>
        </CardContent>
      </Card>
    );
  }

  return (
    <Stack spacing={2}>
      <Card sx={{ borderRadius: 4, bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', boxShadow: 'none' }}>
        <CardContent>
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} alignItems="center">
              <InsightsRoundedIcon sx={{ color: '#FFD3A0' }} />
              <Typography variant="h6" sx={{ color: '#E2E2E3' }}>Results overview</Typography>
            </Stack>

            <Grid container spacing={1.5}>
              <Grid item xs={12} sm={4}>
                <Box sx={{ p: 1.75, borderRadius: 2, border: '1px solid rgba(79, 69, 58, 0.5)', bgcolor: 'rgba(8, 11, 14, 0.78)' }}>
                  <Typography variant="caption" sx={{ color: 'rgba(226, 226, 227, 0.62)' }}>Items found</Typography>
                  <Typography variant="h5" sx={{ color: '#E2E2E3', mt: 0.5 }}>{totalCount}</Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ p: 1.75, borderRadius: 2, border: '1px solid rgba(79, 69, 58, 0.5)', bgcolor: 'rgba(8, 11, 14, 0.78)' }}>
                  <Typography variant="caption" sx={{ color: 'rgba(226, 226, 227, 0.62)' }}>Top field</Typography>
                  <Typography variant="body1" sx={{ color: '#E2E2E3', mt: 0.5 }}>
                    {keyFields.name || 'General records'}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ p: 1.75, borderRadius: 2, border: '1px solid rgba(79, 69, 58, 0.5)', bgcolor: 'rgba(8, 11, 14, 0.78)' }}>
                  <Typography variant="caption" sx={{ color: 'rgba(226, 226, 227, 0.62)' }}>Quick summary</Typography>
                  <Typography variant="body1" sx={{ color: '#E2E2E3', mt: 0.5 }}>{summary}</Typography>
                </Box>
              </Grid>
            </Grid>

            <Box sx={{ p: 2, borderRadius: 2, border: '1px solid rgba(79, 69, 58, 0.5)', bgcolor: 'rgba(8, 11, 14, 0.78)' }}>
              <Typography variant="subtitle2" sx={{ color: '#FFD3A0', mb: 1 }}>
                Insights
              </Typography>
              <Stack spacing={0.75}>
                {insightItems.map((insight) => (
                  <Typography key={insight} variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.76)' }}>
                    {insight}
                  </Typography>
                ))}
              </Stack>
            </Box>

            <Box sx={{ p: 2, borderRadius: 2, border: '1px solid rgba(79, 69, 58, 0.5)', bgcolor: 'rgba(8, 11, 14, 0.78)' }}>
              <Typography variant="subtitle2" sx={{ color: '#FFD3A0', mb: 1 }}>
                Output monitoring
              </Typography>
              <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.78)' }}>
                {outputMonitoring.summaryText}
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1.25 }}>
                <Chip label={`Records: ${totalCount}`} variant="outlined" sx={{ color: '#E2E2E3' }} />
                <Chip label={`Sources: ${outputMonitoring.sourceCount || 0}`} variant="outlined" sx={{ color: '#E2E2E3' }} />
                <Chip
                  label={`Quality: ${
                    outputMonitoring.quality !== null ? `${Math.round(outputMonitoring.quality * 100)}%` : 'Unknown'
                  }`}
                  variant="outlined"
                  sx={{ color: '#E2E2E3' }}
                />
                <Chip
                  label={`Confidence: ${
                    outputMonitoring.confidence !== null ? `${Math.round(outputMonitoring.confidence * 100)}%` : 'Unknown'
                  }`}
                  variant="outlined"
                  sx={{ color: '#E2E2E3' }}
                />
              </Stack>
              {outputMonitoring.issues.length > 0 && (
                <Alert severity="warning" sx={{ mt: 1.5, borderRadius: 2 }}>
                  {outputMonitoring.issues.slice(0, 3).join(' | ')}
                </Alert>
              )}
            </Box>

            <TextField
              fullWidth
              label="Search within results"
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

            {showActions && (
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                {onOpenExports && (
                  <Button variant="contained" onClick={onOpenExports}>
                    Export results
                  </Button>
                )}
                {onOpenWorkspace && (
                  <Button variant="outlined" onClick={onOpenWorkspace}>
                    Open workspace
                  </Button>
                )}
                {onStartNewRequest && (
                  <Button variant="outlined" onClick={onStartNewRequest}>
                    Start new request
                  </Button>
                )}
              </Stack>
            )}
          </Stack>
        </CardContent>
      </Card>

      <Grid container spacing={2}>
        <Grid item xs={12} lg={8}>
          <ResultsTable results={filteredRows} />
        </Grid>
        <Grid item xs={12} lg={4}>
          <Card sx={{ borderRadius: 4, bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', boxShadow: 'none' }}>
            <CardContent>
              <Stack spacing={1.5}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <PreviewRoundedIcon sx={{ color: '#FFD3A0' }} />
                  <Typography variant="h6" sx={{ color: '#E2E2E3' }}>Highlighted item</Typography>
                </Stack>
                {previewItem ? (
                  <>
                    {keyFields.name && <Chip label={`Name: ${keyFields.name}`} sx={{ color: '#E2E2E3', borderColor: 'rgba(79, 69, 58, 0.5)' }} variant="outlined" />}
                    {keyFields.price && <Chip label={`Price: ${keyFields.price}`} sx={{ color: '#30E0A1', borderColor: 'rgba(48,224,161,0.30)' }} variant="outlined" />}
                    {keyFields.availability && <Chip label={`Availability: ${keyFields.availability}`} sx={{ color: '#FFD3A0', borderColor: 'rgba(255, 211, 160, 0.55)' }} variant="outlined" />}
                    <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
                      This is a quick sample from your current view.
                    </Typography>
                    {advancedView && (
                      <Box
                        sx={{
                          p: 1.5,
                          borderRadius: 2,
                          bgcolor: 'rgba(8, 11, 14, 0.78)',
                          border: '1px solid rgba(79, 69, 58, 0.5)',
                          maxHeight: 250,
                          overflow: 'auto',
                          color: '#E2E2E3',
                        }}
                      >
                        <Typography variant="caption" sx={{ color: '#FFD3A0', display: 'block', mb: 0.75 }}>
                          Advanced View (raw data)
                        </Typography>
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                          {JSON.stringify(previewItem || {}, null, 2)}
                        </pre>
                      </Box>
                    )}
                  </>
                ) : (
                  <Typography sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
                    No items match your search right now. Try a broader search term.
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
