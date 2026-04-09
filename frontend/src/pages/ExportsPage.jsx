import React, { useEffect, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import DownloadIcon from '@mui/icons-material/Download';
import DescriptionIcon from '@mui/icons-material/Description';
import TableChartIcon from '@mui/icons-material/TableChart';
import ArticleIcon from '@mui/icons-material/Article';
import api from '../services/api';
import { formatDate, formatFileSize } from '../utils/helpers';

const getFormatIcon = (format) => {
  switch (format?.toLowerCase()) {
    case 'pdf':
      return <DescriptionIcon color="error" />;
    case 'excel':
    case 'xlsx':
      return <TableChartIcon color="success" />;
    case 'word':
    case 'docx':
      return <ArticleIcon color="primary" />;
    default:
      return <DownloadIcon />;
  }
};

const ExportsPage = () => {
  const [exports, setExports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloadMessage, setDownloadMessage] = useState('');

  useEffect(() => {
    fetchExports();
  }, []);

  const fetchExports = async () => {
    try {
      setLoading(true);
      setError('');
      const exportItems = await api.getExports();
      setExports(exportItems);
    } catch (err) {
      setError('We could not load your exports right now.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (exportId, filename) => {
    try {
      const blobData = await api.downloadExport(exportId);
      const blob = new Blob([blobData]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || `export-${exportId}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setDownloadMessage(`Your export${filename ? `, ${filename},` : ''} is ready to download.`);
    } catch (err) {
      setError('We could not download that export. Please try again.');
    }
  };

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h3" gutterBottom>
          Exports
        </Typography>
        <Typography color="text.secondary">
          Your finished files live here. Download them when you are ready or return to a workspace to create a new one.
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}
      {downloadMessage && <Alert severity="success">{downloadMessage}</Alert>}

      {!loading && exports.length > 0 && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Card sx={{ borderRadius: 4, height: '100%' }}>
              <CardContent>
                <Typography variant="overline">Total Exports</Typography>
                <Typography variant="h4">{exports.length}</Typography>
                <Typography color="text.secondary">Files created from completed runs</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card sx={{ borderRadius: 4, height: '100%' }}>
              <CardContent>
                <Typography variant="overline">Ready To Download</Typography>
                <Typography variant="h4">{exports.filter((item) => item.file_path).length}</Typography>
                <Typography color="text.secondary">Exports with a download file available</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card sx={{ borderRadius: 4, height: '100%' }}>
              <CardContent>
                <Typography variant="overline">Formats Used</Typography>
                <Typography variant="h4">
                  {new Set(exports.map((item) => item.format).filter(Boolean)).size}
                </Typography>
                <Typography color="text.secondary">Different export formats in your history</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {loading ? (
        <Card sx={{ borderRadius: 4 }}>
          <CardContent>
            <Stack spacing={2} alignItems="center" sx={{ py: 6 }}>
              <CircularProgress />
              <Typography variant="h6">Loading exports</Typography>
              <Typography color="text.secondary" align="center">
                We are checking which files are ready for download.
              </Typography>
            </Stack>
          </CardContent>
        </Card>
      ) : exports.length === 0 ? (
        <Card sx={{ borderRadius: 4 }}>
          <CardContent>
            <Typography variant="h6">No exports yet</Typography>
            <Typography color="text.secondary">
              Once a run is complete, you can export its results from the workspace page.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={2}>
          {exports.map((exportItem) => {
            const fileName = exportItem.file_path?.split('/').pop() || null;
            return (
              <Grid item xs={12} md={6} lg={4} key={exportItem.id}>
                <Card sx={{ borderRadius: 4, height: '100%' }}>
                  <CardContent>
                    <Stack spacing={2}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {getFormatIcon(exportItem.format)}
                        <Typography variant="h6">
                          {exportItem.format?.toUpperCase() || 'FILE'} Export
                        </Typography>
                      </Box>

                      <Typography variant="body2" color="text.secondary">
                        Export ready
                      </Typography>

                      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                        <Chip label={`Run ${exportItem.run_id || '-'}`} size="small" variant="outlined" />
                        <Chip label={(exportItem.format || 'file').toUpperCase()} size="small" color="primary" variant="outlined" />
                        <Chip
                          label={exportItem.file_size ? formatFileSize(exportItem.file_size) : 'Size pending'}
                          size="small"
                          variant="outlined"
                        />
                      </Stack>

                      <Box>
                        <Typography variant="subtitle2">{fileName || 'File path will appear when ready'}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          Created {exportItem.created_at ? formatDate(exportItem.created_at) : '-'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {exportItem.file_path
                            ? 'This file is ready to download.'
                            : 'The file path has not been published yet.'}
                        </Typography>
                      </Box>

                      <Button
                        variant="contained"
                        startIcon={<DownloadIcon />}
                        onClick={() => handleDownload(exportItem.id, fileName)}
                        disabled={!exportItem.file_path}
                      >
                        Download
                      </Button>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}
    </Stack>
  );
};

export default ExportsPage;
