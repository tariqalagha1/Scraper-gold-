import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import HistoryEduRoundedIcon from '@mui/icons-material/HistoryEduRounded';

const RecentRequestsCard = ({ requests = [], onReuse }) => (
  <Card sx={{ borderRadius: 4, height: '100%', bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', boxShadow: 'none' }}>
    <CardContent>
      <Stack spacing={1.5}>
        <Stack direction="row" spacing={1} alignItems="center">
          <HistoryEduRoundedIcon sx={{ color: '#FFD3A0' }} />
          <Typography variant="h6" sx={{ color: '#E2E2E3' }}>Recent Requests</Typography>
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
          Reuse a past scraping request without retyping the URL and prompt.
        </Typography>

        {requests.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
            Your recent scraping requests will appear here.
          </Typography>
        ) : (
          requests.map((item, index) => (
            <Button
              key={`${item.url}-${index}`}
              variant="outlined"
              sx={{
                justifyContent: 'flex-start',
                textAlign: 'left',
                borderRadius: 3,
                py: 1.5,
                textTransform: 'none',
                borderColor: 'rgba(79, 69, 58, 0.5)',
                bgcolor: 'rgba(8, 11, 14, 0.78)',
                color: '#E2E2E3',
                '&:hover': {
                  borderColor: 'rgba(240, 189, 127, 0.52)',
                  backgroundColor: 'rgba(13, 16, 20, 0.85)',
                },
              }}
              onClick={() => onReuse(item)}
            >
              <Stack spacing={0.5} sx={{ alignItems: 'flex-start' }}>
                <Typography variant="subtitle2">{item.title || item.prompt}</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
                  {item.url}
                </Typography>
              </Stack>
            </Button>
          ))
        )}
      </Stack>
    </CardContent>
  </Card>
);

export default RecentRequestsCard;
