import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { formatDate } from '../utils/helpers';

const ActivityFeedCard = ({ items = [], title = 'Recent Activity', helperText = 'A simple timeline of the latest workspace events.' }) => (
  <Card sx={{ borderRadius: 4, height: '100%', bgcolor: 'rgba(28, 31, 35, 0.84)', border: '1px solid rgba(79, 69, 58, 0.5)', color: '#E2E2E3', boxShadow: 'none' }}>
    <CardContent>
      <Stack spacing={2}>
        <div>
          <Typography variant="h6" sx={{ color: '#E2E2E3' }}>{title}</Typography>
          <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
            {helperText}
          </Typography>
        </div>

        {items.length === 0 ? (
          <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
            No activity yet. Once your team starts creating jobs, runs, or exports, it will show up here.
          </Typography>
        ) : (
          items.map((item, index) => (
            <Card key={`${item.type}-${item.id || index}`} variant="outlined" sx={{ borderRadius: 3, bgcolor: 'rgba(8, 11, 14, 0.78)', borderColor: 'rgba(79, 69, 58, 0.5)' }}>
              <CardContent sx={{ '&:last-child': { pb: 2 } }}>
                <Stack spacing={1}>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
                    <Chip label={item.type_label} size="small" variant="outlined" sx={{ color: '#FFD3A0', borderColor: 'rgba(255, 211, 160, 0.45)' }} />
                    {item.status && <Chip label={item.status} size="small" color={item.status_color || 'default'} />}
                  </Stack>
                  <Typography variant="subtitle2" sx={{ color: '#E2E2E3' }}>{item.title}</Typography>
                  {item.subtitle && (
                    <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
                      {item.subtitle}
                    </Typography>
                  )}
                  <Typography variant="caption" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
                    {formatDate(item.timestamp)}
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          ))
        )}
      </Stack>
    </CardContent>
  </Card>
);

export default ActivityFeedCard;
