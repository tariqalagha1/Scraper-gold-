import React, { useMemo, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded';
import TravelExploreRoundedIcon from '@mui/icons-material/TravelExploreRounded';
import { interpretCommand } from '../assistant/orchestrator';

const AICommandPanel = ({ initialUrl = '', initialPrompt = '', onStart }) => {
  const [url, setUrl] = useState(initialUrl);
  const [prompt, setPrompt] = useState(initialPrompt);
  const [error, setError] = useState('');

  const preview = useMemo(() => interpretCommand({ url, prompt }), [url, prompt]);

  const handleStart = () => {
    if (!url.trim()) {
      setError('Please enter a website URL first.');
      return;
    }

    setError('');
    onStart(preview, prompt);
  };

  return (
    <Card
      sx={{
        borderRadius: 4,
        boxShadow: 'none',
        overflow: 'hidden',
        bgcolor: 'transparent',
        border: '1px solid rgba(79, 69, 58, 0.5)',
      }}
    >
      <CardContent sx={{ p: { xs: 3, md: 4 } }}>
        <Stack spacing={2.5}>
          <Box>
            <Stack direction="row" spacing={1.25} alignItems="center">
              <AutoAwesomeIcon sx={{ color: '#FFD3A0' }} />
              <Typography variant="h4" gutterBottom sx={{ color: '#E2E2E3', mb: 0 }}>
                Tell Smart Scraper what you need
              </Typography>
            </Stack>
            <Typography color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)', mt: 1 }}>
              Describe the website and the data you want in plain English.
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
              <Chip label="Extract products" size="small" variant="outlined" sx={{ color: '#E2E2E3', borderColor: 'rgba(79, 69, 58, 0.55)' }} />
              <Chip label="Collect PDFs" size="small" variant="outlined" sx={{ color: '#E2E2E3', borderColor: 'rgba(79, 69, 58, 0.55)' }} />
              <Chip label="Capture table rows" size="small" variant="outlined" sx={{ color: '#E2E2E3', borderColor: 'rgba(79, 69, 58, 0.55)' }} />
            </Stack>
          </Box>

          {error && <Alert severity="error" sx={{ borderRadius: 3 }}>{error}</Alert>}

          <TextField
            label="Website URL"
            placeholder="https://books.toscrape.com"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            fullWidth
            InputProps={{
              startAdornment: <TravelExploreRoundedIcon sx={{ color: 'rgba(226, 226, 227, 0.72)', mr: 1 }} />,
            }}
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

          <TextField
            label="What do you want to find?"
            placeholder="Extract titles, prices, and availability from this website"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            multiline
            minRows={3}
            fullWidth
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

          <Box sx={{ p: 2.5, borderRadius: 3, bgcolor: 'rgba(8, 11, 14, 0.78)', border: '1px solid rgba(79, 69, 58, 0.5)' }}>
            <Stack spacing={1.5}>
              <Typography variant="subtitle2" sx={{ color: '#E2E2E3' }}>Preview before creating the job</Typography>
              <Chip
                label={`Detected type: ${preview.scrape_type}`}
                color="primary"
                variant="outlined"
                sx={{ width: 'fit-content', color: '#FFD3A0', borderColor: 'rgba(255, 211, 160, 0.6)' }}
              />
              <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>URL: {preview.url || 'Not set yet'}</Typography>
              <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>{preview.explanation}</Typography>
            </Stack>
          </Box>

          <Button
            variant="contained"
            size="large"
            onClick={handleStart}
            startIcon={<PlayArrowRoundedIcon />}
            sx={{
              alignSelf: { xs: 'stretch', sm: 'flex-start' },
              px: 4,
              borderRadius: 3,
              background: 'linear-gradient(135deg, #FFD3A0 0%, #E8B678 100%)',
              color: '#121415',
              boxShadow: 'inset 0 4px 12px rgba(255,255,255,0.15), 0 8px 30px rgba(240,189,127,0.22)',
              '&:hover': {
                background: 'linear-gradient(135deg, #FFD9AA 0%, #F0BD7F 100%)',
                boxShadow: 'inset 0 4px 12px rgba(255,255,255,0.15), 0 10px 36px rgba(240,189,127,0.28)',
              },
            }}
          >
            Review Request
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
};


export default AICommandPanel;
