/**
 * Results table component to display scraped results.
 */
import React from 'react';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';

const ResultsTable = ({ results }) => {
  const normalizedResults = (results || []).map((result, index) => {
    const data = result?.data_json && typeof result.data_json === 'object' ? result.data_json : result || {};
    return {
      id: result?.id || `record-${index + 1}`,
      data_type: result?.data_type || 'record',
      data_json: data,
    };
  });

  if (!normalizedResults || normalizedResults.length === 0) {
    return (
      <Paper sx={{ p: 3, borderRadius: 4, bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', boxShadow: 'none' }}>
        <Stack spacing={1}>
          <Typography variant="h6" sx={{ color: '#E2E2E3' }}>No results yet</Typography>
          <Typography color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
            When the run finds matching data, it will appear here in a table you can review and export.
          </Typography>
        </Stack>
      </Paper>
    );
  }

  // Get all unique keys from results
  const allKeys = [...new Set(normalizedResults.flatMap((r) => Object.keys(r.data_json || {})))];

  return (
    <TableContainer component={Paper} sx={{ borderRadius: 4, bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', boxShadow: 'none' }}>
      <Stack direction="row" spacing={1} sx={{ p: 2, borderBottom: '1px solid', borderColor: 'rgba(79, 69, 58, 0.45)' }} flexWrap="wrap" useFlexGap>
        <Chip label={`${normalizedResults.length} rows`} size="small" variant="outlined" sx={{ color: '#E2E2E3', borderColor: 'rgba(79, 69, 58, 0.5)' }} />
        <Chip label={`${Math.min(allKeys.length, 5)} visible fields`} size="small" variant="outlined" />
      </Stack>
      <Table sx={{ '& .MuiTableCell-root': { color: '#E2E2E3', borderColor: 'rgba(79, 69, 58, 0.35)' } }}>
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Type</TableCell>
            {allKeys.slice(0, 5).map((key) => (
              <TableCell key={key}>{key}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {normalizedResults.map((result) => (
            <TableRow key={result.id}>
              <TableCell>{result.id}</TableCell>
              <TableCell>{result.data_type}</TableCell>
              {allKeys.slice(0, 5).map((key) => (
                <TableCell key={key}>
                  {String(result.data_json?.[key] || '').substring(0, 100)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default ResultsTable;
