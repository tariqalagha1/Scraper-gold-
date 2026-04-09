import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { formatDate } from '../utils/helpers';

const ActivityFeedCard = ({ items = [], title = 'Recent Activity', helperText = 'A simple timeline of the latest workspace events.' }) => (
  <Card sx={{ borderRadius: 4, height: '100%' }}>
    <CardContent>
      <Stack spacing={2}>
        <div>
          <Typography variant="h6">{title}</Typography>
          <Typography variant="body2" color="text.secondary">
            {helperText}
          </Typography>
        </div>

        {items.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No activity yet. Once your team starts creating jobs, runs, or exports, it will show up here.
          </Typography>
        ) : (
          items.map((item, index) => (
            <Card key={`${item.type}-${item.id || index}`} variant="outlined" sx={{ borderRadius: 3 }}>
              <CardContent sx={{ '&:last-child': { pb: 2 } }}>
                <Stack spacing={1}>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
                    <Chip label={item.type_label} size="small" variant="outlined" />
                    {item.status && <Chip label={item.status} size="small" color={item.status_color || 'default'} />}
                  </Stack>
                  <Typography variant="subtitle2">{item.title}</Typography>
                  {item.subtitle && (
                    <Typography variant="body2" color="text.secondary">
                      {item.subtitle}
                    </Typography>
                  )}
                  <Typography variant="caption" color="text.secondary">
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
