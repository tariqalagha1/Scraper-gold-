import React from 'react';
import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import Drawer from '@mui/material/Drawer';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import QuickStatusCards from './QuickStatusCards';
import RecentRunsCard from './RecentRunsCard';
import RecentRequestsCard from './RecentRequestsCard';
import ActivityTimeline from './ActivityTimeline';
import DiagnosticsWidget from './DiagnosticsWidget';

const AdvancedDetailsDrawer = ({
  open,
  onClose,
  requestPayload,
  responsePayload,
  jobs,
  runs,
  accountSummary,
  latestRunsByJob,
  recentRequests,
  onReuseRequest,
}) => (
  <Drawer
    anchor="right"
    open={open}
    onClose={onClose}
    PaperProps={{
      sx: {
        width: { xs: '100%', md: 560 },
        bgcolor: '#0C1117',
        color: '#E2E2E3',
        borderLeft: '1px solid rgba(79, 69, 58, 0.5)',
      },
    }}
  >
    <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
      <Stack spacing={2.5}>
        <div>
          <Typography variant="h6">AdvancedDetailsDrawer</Typography>
          <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)', mt: 0.75 }}>
            Advanced diagnostics, workspace metrics, and raw payloads.
          </Typography>
        </div>

        <QuickStatusCards jobs={jobs} runs={runs} accountSummary={accountSummary} />

        <RecentRunsCard jobs={jobs} latestRunsByJob={latestRunsByJob} advancedView />
        <RecentRequestsCard requests={recentRequests} onReuse={onReuseRequest} />

        <ActivityTimeline />
        <DiagnosticsWidget />

        <Divider sx={{ borderColor: 'rgba(79, 69, 58, 0.5)' }} />

        <div>
          <Typography variant="subtitle2" sx={{ color: '#F6D28F', mb: 0.75 }}>
            Raw request payload
          </Typography>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 1.5,
              borderRadius: 2,
              border: '1px solid rgba(79, 69, 58, 0.4)',
              bgcolor: 'rgba(5, 8, 12, 0.9)',
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, Courier New, monospace',
              fontSize: 12,
              lineHeight: 1.5,
              color: 'rgba(226, 226, 227, 0.85)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {JSON.stringify(requestPayload || {}, null, 2)}
          </Box>
        </div>

        <div>
          <Typography variant="subtitle2" sx={{ color: '#F6D28F', mb: 0.75 }}>
            Raw response payload
          </Typography>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 1.5,
              borderRadius: 2,
              border: '1px solid rgba(79, 69, 58, 0.4)',
              bgcolor: 'rgba(5, 8, 12, 0.9)',
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, Courier New, monospace',
              fontSize: 12,
              lineHeight: 1.5,
              color: 'rgba(226, 226, 227, 0.85)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {JSON.stringify(responsePayload || {}, null, 2)}
          </Box>
        </div>
      </Stack>
    </Box>
  </Drawer>
);

export default AdvancedDetailsDrawer;
