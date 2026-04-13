import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import HistoryRoundedIcon from '@mui/icons-material/HistoryRounded';
import OpenInNewRoundedIcon from '@mui/icons-material/OpenInNewRounded';
import StopRoundedIcon from '@mui/icons-material/StopRounded';
import SecurityRoundedIcon from '@mui/icons-material/SecurityRounded';
import DescriptionRoundedIcon from '@mui/icons-material/DescriptionRounded';
import api from '../services/api';
import { formatDate, formatStatus, getErrorMessage, getStatusColor, truncateString } from '../utils/helpers';

const toCompressionPercentage = (ratio) => {
  const normalizedRatio = Number(ratio);
  if (!Number.isFinite(normalizedRatio)) {
    return null;
  }

  const boundedRatio = Math.min(1, Math.max(0, normalizedRatio));
  return Math.round((1 - boundedRatio) * 100);
};

const RecentRunsCard = ({ jobs = [], latestRunsByJob = {} }) => {
  const [markdownPreviewOpen, setMarkdownPreviewOpen] = useState(false);
  const [markdownPreviewLoading, setMarkdownPreviewLoading] = useState(false);
  const [markdownPreviewError, setMarkdownPreviewError] = useState('');
  const [markdownPreviewContent, setMarkdownPreviewContent] = useState('');
  const [markdownPreviewPath, setMarkdownPreviewPath] = useState('');
  const [cancelingRunIds, setCancelingRunIds] = useState(new Set());

  const recentItems = jobs
    .map((job) => ({
      job,
      run: latestRunsByJob[job.id] || null,
    }))
    .sort((left, right) => {
      const leftDate = new Date(left.run?.created_at || left.job.created_at || 0).getTime();
      const rightDate = new Date(right.run?.created_at || right.job.created_at || 0).getTime();
      return rightDate - leftDate;
    })
    .slice(0, 5);

  const closeMarkdownPreview = () => {
    setMarkdownPreviewOpen(false);
    setMarkdownPreviewLoading(false);
    setMarkdownPreviewError('');
    setMarkdownPreviewContent('');
    setMarkdownPreviewPath('');
  };

  const openMarkdownPreview = async (run) => {
    if (!run?.id) {
      return;
    }

    setMarkdownPreviewOpen(true);
    setMarkdownPreviewLoading(true);
    setMarkdownPreviewError('');
    setMarkdownPreviewContent('');
    setMarkdownPreviewPath(run.markdown_snapshot_path || '');

    try {
      const payload = await api.getRunMarkdown(run.id);
      setMarkdownPreviewContent(String(payload?.markdown || '').trim());
      setMarkdownPreviewPath(payload?.snapshot_path || run.markdown_snapshot_path || '');
    } catch (error) {
      // Handle missing markdown snapshot gracefully (404 means not yet generated)
      if (error.response?.status === 404) {
        setMarkdownPreviewError('Markdown snapshot not yet available for this run.');
      } else {
        setMarkdownPreviewError(
          getErrorMessage(error, 'Could not load semantic markdown for this run.')
        );
      }
    } finally {
      setMarkdownPreviewLoading(false);
    }
  };

  const handleCancelRun = async (runId) => {
    if (!window.confirm('Are you sure you want to cancel this run?')) return;

    try {
      setCancelingRunIds(prev => new Set([...prev, runId]));
      await api.cancelRun(runId);
      // Optionally refresh the runs after canceling
      window.location.reload();
    } catch (error) {
      console.error('Error canceling run:', error);
      alert('Failed to cancel run');
      setCancelingRunIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(runId);
        return newSet;
      });
    }
  };

  return (
    <>
      <Card sx={{ borderRadius: 4, height: '100%', bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', boxShadow: 'none' }}>
        <CardContent>
          <Stack spacing={1.5}>
            <Stack direction="row" spacing={1} alignItems="center">
              <HistoryRoundedIcon sx={{ color: '#FFD3A0' }} />
              <Typography variant="h6" sx={{ color: '#E2E2E3' }}>Recent Runs</Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
              Open a workspace to follow progress, results, and exports.
            </Typography>

            {recentItems.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
                No runs yet. Create your first request above.
              </Typography>
            ) : (
              recentItems.map(({ job, run }) => {
                const compressionPercentage = toCompressionPercentage(run?.token_compression_ratio);
                return (
                  <Card key={job.id} variant="outlined" sx={{ borderRadius: 3, bgcolor: 'rgba(8, 11, 14, 0.78)', borderColor: 'rgba(79, 69, 58, 0.5)' }}>
                    <CardContent sx={{ '&:last-child': { pb: 2 } }}>
                      <Stack
                        direction={{ xs: 'column', md: 'row' }}
                        spacing={1.5}
                        justifyContent="space-between"
                        alignItems={{ xs: 'flex-start', md: 'center' }}
                      >
                        <Box>
                          <Typography variant="subtitle2" sx={{ color: '#E2E2E3' }}>
                            {truncateString(job.url, 70)}
                          </Typography>
                          <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                            <Chip label={job.scrape_type} size="small" variant="outlined" sx={{ color: '#E2E2E3', borderColor: 'rgba(79, 69, 58, 0.5)' }} />
                            {run ? (
                              <Chip
                                label={`${formatStatus(run.status)} ${run.progress ?? 0}%`}
                                size="small"
                                color={getStatusColor(run.status)}
                              />
                            ) : (
                              <Chip label="No run yet" size="small" variant="outlined" />
                            )}
                            {run?.stealth_engaged && (
                              <Tooltip title="Stealth mode active for this run">
                                <Box
                                  sx={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    width: 24,
                                    height: 24,
                                    borderRadius: '50%',
                                    border: '1px solid rgba(240, 189, 127, 0.52)',
                                    backgroundColor: 'rgba(240, 189, 127, 0.08)',
                                  }}
                                >
                                  <SecurityRoundedIcon sx={{ fontSize: 15, color: '#F0BD7F' }} />
                                </Box>
                              </Tooltip>
                            )}
                            {compressionPercentage !== null && (
                              <Chip
                                label={`Compressed: ${compressionPercentage}%`}
                                size="small"
                                variant="outlined"
                                sx={{
                                  color: '#F0BD7F',
                                  borderColor: 'rgba(240, 189, 127, 0.52)',
                                  backgroundColor: 'rgba(240, 189, 127, 0.08)',
                                }}
                              />
                            )}
                            {run?.markdown_snapshot_path && (
                              <Tooltip title="View semantic markdown">
                                <IconButton
                                  size="small"
                                  onClick={() => openMarkdownPreview(run)}
                                  aria-label="View semantic markdown"
                                  sx={{
                                    border: '1px solid rgba(79, 69, 58, 0.5)',
                                    color: '#F0BD7F',
                                    borderRadius: 2,
                                    '&:hover': {
                                      borderColor: 'rgba(240, 189, 127, 0.52)',
                                      backgroundColor: 'rgba(240, 189, 127, 0.08)',
                                    },
                                  }}
                                >
                                  <DescriptionRoundedIcon sx={{ fontSize: 16 }} />
                                </IconButton>
                              </Tooltip>
                            )}
                          </Box>
                          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', color: 'rgba(226, 226, 227, 0.72)' }}>
                            {run ? `Updated ${formatDate(run.created_at)}` : `Created ${formatDate(job.created_at)}`}
                          </Typography>
                        </Box>

                        <Stack direction="row" spacing={1} alignItems="center">
                          <Button
                            component={Link}
                            to={`/jobs/${job.id}`}
                            variant="outlined"
                            endIcon={<OpenInNewRoundedIcon />}
                            sx={{
                              textTransform: 'none',
                              whiteSpace: 'nowrap',
                              borderRadius: 3,
                              borderColor: 'rgba(79, 69, 58, 0.5)',
                              color: '#E2E2E3',
                              '&:hover': {
                                borderColor: 'rgba(240, 189, 127, 0.52)',
                                backgroundColor: 'rgba(13, 16, 20, 0.85)',
                              },
                            }}
                          >
                            Open Workspace
                          </Button>
                          {run && ['running', 'pending', 'queued'].includes(run.status) && (
                            <Tooltip title="Cancel this run">
                              <Button
                                onClick={() => handleCancelRun(run.id)}
                                disabled={cancelingRunIds.has(run.id)}
                                variant="outlined"
                                size="small"
                                endIcon={<StopRoundedIcon />}
                                sx={{
                                  textTransform: 'none',
                                  whiteSpace: 'nowrap',
                                  borderRadius: 3,
                                  borderColor: 'rgba(239, 68, 68, 0.5)',
                                  color: '#EF4444',
                                  '&:hover': {
                                    borderColor: 'rgba(239, 68, 68, 0.8)',
                                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                  },
                                  '&:disabled': {
                                    opacity: 0.6,
                                    cursor: 'not-allowed',
                                  },
                                }}
                              >
                                {cancelingRunIds.has(run.id) ? 'Canceling...' : 'Cancel'}
                              </Button>
                            </Tooltip>
                          )}
                        </Stack>
                      </Stack>
                    </CardContent>
                  </Card>
                );
              })
            )}
          </Stack>
        </CardContent>
      </Card>

      <Dialog
        open={markdownPreviewOpen}
        onClose={closeMarkdownPreview}
        fullWidth
        maxWidth="md"
        PaperProps={{
          sx: {
            borderRadius: 3,
            bgcolor: 'rgba(17, 20, 24, 0.98)',
            border: '1px solid rgba(79, 69, 58, 0.6)',
          },
        }}
      >
        <DialogTitle sx={{ color: '#E2E2E3' }}>Semantic Markdown Snapshot</DialogTitle>
        <DialogContent dividers sx={{ borderColor: 'rgba(79, 69, 58, 0.5)' }}>
          {markdownPreviewPath && (
            <Typography variant="caption" sx={{ color: 'rgba(226, 226, 227, 0.72)', display: 'block', mb: 1 }}>
              {markdownPreviewPath}
            </Typography>
          )}
          {markdownPreviewLoading ? (
            <Stack direction="row" spacing={1} alignItems="center" sx={{ color: '#E2E2E3' }}>
              <CircularProgress size={18} sx={{ color: '#F0BD7F' }} />
              <Typography variant="body2">Loading markdown preview...</Typography>
            </Stack>
          ) : markdownPreviewError ? (
            <Alert severity="error">{markdownPreviewError}</Alert>
          ) : (
            <Box
              component="pre"
              sx={{
                m: 0,
                p: 1.5,
                borderRadius: 2,
                border: '1px solid rgba(79, 69, 58, 0.5)',
                backgroundColor: 'rgba(8, 11, 14, 0.78)',
                color: '#E2E2E3',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                fontSize: '0.82rem',
                lineHeight: 1.5,
                maxHeight: 420,
                overflow: 'auto',
              }}
            >
              {markdownPreviewContent || 'No semantic markdown content found for this run.'}
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default RecentRunsCard;
