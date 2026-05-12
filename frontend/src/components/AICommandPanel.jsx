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
import TaskAltRoundedIcon from '@mui/icons-material/TaskAltRounded';
import TravelExploreRoundedIcon from '@mui/icons-material/TravelExploreRounded';
import api, { extractApiErrorMessage } from '../services/api';
import { interpretCommand } from '../assistant/orchestrator';

const REQUEST_TEMPLATES = [
  {
    label: 'Product Listing',
    prompt: 'Collect product name, current price, availability, and product link from each listing page.',
  },
  {
    label: 'Contact Directory',
    prompt: 'Collect business name, phone number, email, and website from this directory.',
  },
  {
    label: 'Article Tracking',
    prompt: 'Collect article title, publication date, author, and article URL.',
  },
];

const EXAMPLE_REQUESTS = [
  'Find all products with title, price, stock status, and page link.',
  'Collect all event names, dates, and registration links from this site.',
  'Gather all team member names, roles, and profile links.',
];

const getInputSx = () => ({
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
});

const AICommandPanel = ({ initialUrl = '', initialPrompt = '', onStart, advancedView = false }) => {
  const [url, setUrl] = useState(initialUrl);
  const [requestText, setRequestText] = useState(initialPrompt || '');
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantError, setAssistantError] = useState('');
  const [assistantMessage, setAssistantMessage] = useState('');
  const [refinedPrompt, setRefinedPrompt] = useState('');
  const [recommendedType, setRecommendedType] = useState('');
  const [readyToApply, setReadyToApply] = useState(false);
  const [clarifyingQuestions, setClarifyingQuestions] = useState([]);
  const [followUpAnswers, setFollowUpAnswers] = useState({});

  const effectivePrompt = useMemo(() => {
    const refined = refinedPrompt.trim();
    if (refined) return refined;
    return requestText.trim();
  }, [refinedPrompt, requestText]);

  const preview = useMemo(
    () => interpretCommand({ url: url.trim(), prompt: effectivePrompt }),
    [url, effectivePrompt]
  );

  const structuredPreview = useMemo(
    () => ({
      task_type: recommendedType || preview.scrape_type,
      payload: {
        url: url || '[set website URL]',
        prompt: effectivePrompt || '[describe your request]',
        max_pages: 10,
        follow_pagination: true,
      },
    }),
    [effectivePrompt, preview.scrape_type, recommendedType, url]
  );

  const handleStart = () => {
    if (!url.trim()) {
      setAssistantError('Please add the website URL first.');
      return;
    }
    if (!effectivePrompt.trim()) {
      setAssistantError('Describe what you want to collect before running.');
      return;
    }

    setAssistantError('');
    onStart(preview, effectivePrompt);
  };

  const handleRefineRequest = async () => {
    const intentText = requestText.trim();
    if (!intentText) {
      setAssistantError('Write your request first, then click Refine Request.');
      return;
    }

    setAssistantLoading(true);
    setAssistantError('');

    const answeredFollowUps = clarifyingQuestions
      .map((question) => {
        const answer = String(followUpAnswers[question] || '').trim();
        if (!answer) return null;
        return { role: 'user', content: `Question: ${question}\nAnswer: ${answer}` };
      })
      .filter(Boolean);

    try {
      const response = await api.refineScrapeRequest({
        url: url.trim() || null,
        draft_prompt: effectivePrompt || null,
        user_message: intentText,
        conversation: answeredFollowUps,
      });

      setAssistantMessage(response.assistant_message || '');
      setRefinedPrompt(response.refined_prompt || '');
      setRecommendedType(response.recommended_scrape_type || '');
      setReadyToApply(Boolean(response.ready_to_apply));
      setClarifyingQuestions(Array.isArray(response.clarifying_questions) ? response.clarifying_questions : []);
    } catch (requestError) {
      setAssistantError(
        extractApiErrorMessage(requestError, 'Request Assistant is temporarily unavailable. Please try again.')
      );
    } finally {
      setAssistantLoading(false);
    }
  };

  const handleUseRefinedRequest = () => {
    if (!refinedPrompt.trim()) {
      return;
    }
    setRequestText(refinedPrompt);
    setAssistantError('');
  };

  const handleTemplateSelect = (templatePrompt) => {
    setRequestText(templatePrompt);
    setRefinedPrompt('');
    setAssistantMessage('');
    setReadyToApply(false);
    setClarifyingQuestions([]);
    setFollowUpAnswers({});
    setAssistantError('');
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
                What would you like to collect?
              </Typography>
            </Stack>
            <Typography color="text.secondary" sx={{ color: 'rgba(226, 226, 227, 0.72)', mt: 1 }}>
              Type your request in plain language. We will help refine it before you run.
            </Typography>
          </Box>

          {assistantError && <Alert severity="error" sx={{ borderRadius: 3 }}>{assistantError}</Alert>}

          <TextField
            label="Website URL"
            placeholder="https://books.toscrape.com"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            fullWidth
            InputProps={{
              startAdornment: <TravelExploreRoundedIcon sx={{ color: 'rgba(226, 226, 227, 0.72)', mr: 1 }} />,
            }}
            sx={getInputSx()}
          />

          <TextField
            label="Your request"
            placeholder="Find title, price, and availability for each product."
            value={requestText}
            onChange={(event) => setRequestText(event.target.value)}
            multiline
            minRows={3}
            fullWidth
            sx={getInputSx()}
          />

          <Box sx={{ p: 2, borderRadius: 3, bgcolor: 'rgba(8, 11, 14, 0.78)', border: '1px solid rgba(79, 69, 58, 0.5)' }}>
            <Typography variant="subtitle2" sx={{ color: '#E2E2E3', mb: 1.25 }}>
              Quick templates
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {REQUEST_TEMPLATES.map((template) => (
                <Chip
                  key={template.label}
                  label={template.label}
                  onClick={() => handleTemplateSelect(template.prompt)}
                  clickable
                  variant="outlined"
                  sx={{ color: '#FFD3A0', borderColor: 'rgba(255, 211, 160, 0.58)' }}
                />
              ))}
            </Stack>

            <Typography variant="caption" sx={{ color: 'rgba(226, 226, 227, 0.72)', display: 'block', mt: 1.5, mb: 0.75 }}>
              Example requests
            </Typography>
            <Stack spacing={0.75}>
              {EXAMPLE_REQUESTS.map((example) => (
                <Button
                  key={example}
                  type="button"
                  variant="text"
                  onClick={() => handleTemplateSelect(example)}
                  sx={{
                    justifyContent: 'flex-start',
                    textTransform: 'none',
                    color: 'rgba(226, 226, 227, 0.78)',
                    px: 1,
                  }}
                >
                  {example}
                </Button>
              ))}
            </Stack>
          </Box>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25}>
            <Button
              type="button"
              variant="outlined"
              onClick={handleRefineRequest}
              disabled={assistantLoading}
              sx={{
                borderRadius: 3,
                color: '#FFD3A0',
                borderColor: 'rgba(255, 211, 160, 0.58)',
                '&:hover': {
                  borderColor: '#FFD3A0',
                  backgroundColor: 'rgba(255, 211, 160, 0.08)',
                },
              }}
            >
              {assistantLoading ? 'Refining...' : 'Refine Request'}
            </Button>

            <Button
              variant="contained"
              onClick={handleStart}
              startIcon={<PlayArrowRoundedIcon />}
              sx={{
                borderRadius: 3,
                px: 3.5,
                background: 'linear-gradient(135deg, #FFD3A0 0%, #E8B678 100%)',
                color: '#121415',
                boxShadow: 'inset 0 4px 12px rgba(255,255,255,0.15), 0 8px 30px rgba(240,189,127,0.22)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #FFD9AA 0%, #F0BD7F 100%)',
                  boxShadow: 'inset 0 4px 12px rgba(255,255,255,0.15), 0 10px 36px rgba(240,189,127,0.28)',
                },
              }}
            >
              Run Request
            </Button>
          </Stack>

          {refinedPrompt && (
            <Box sx={{ p: 2.5, borderRadius: 3, bgcolor: 'rgba(8, 11, 14, 0.78)', border: '1px solid rgba(79, 69, 58, 0.5)' }}>
              <Stack spacing={1.5}>
                <Typography variant="subtitle1" sx={{ color: '#E2E2E3', fontWeight: 700 }}>
                  Refined request
                </Typography>
                <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.82)', whiteSpace: 'pre-wrap' }}>
                  {refinedPrompt}
                </Typography>

                {assistantMessage && (
                  <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
                    {assistantMessage}
                  </Typography>
                )}

                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} useFlexGap>
                  <Chip
                    size="small"
                    label={readyToApply ? 'Ready to run' : 'Needs a bit more detail'}
                    variant="outlined"
                    sx={{ color: readyToApply ? '#A5E6B8' : '#F6D28F', borderColor: 'rgba(255, 211, 160, 0.45)' }}
                  />
                  {recommendedType && (
                    <Chip
                      size="small"
                      label={`Suggested type: ${recommendedType}`}
                      variant="outlined"
                      sx={{ color: '#FFD3A0', borderColor: 'rgba(255, 211, 160, 0.55)' }}
                    />
                  )}
                </Stack>

                {clarifyingQuestions.length > 0 && (
                  <Stack spacing={1.25}>
                    <Typography variant="caption" sx={{ color: '#F6D28F' }}>
                      Guided follow-up questions
                    </Typography>
                    {clarifyingQuestions.map((question) => (
                      <TextField
                        key={question}
                        label={question}
                        value={followUpAnswers[question] || ''}
                        onChange={(event) =>
                          setFollowUpAnswers((previous) => ({ ...previous, [question]: event.target.value }))
                        }
                        fullWidth
                        sx={getInputSx()}
                      />
                    ))}
                    <Typography variant="caption" sx={{ color: 'rgba(226, 226, 227, 0.66)' }}>
                      Answer these, then click Refine Request again for a stronger final brief.
                    </Typography>
                  </Stack>
                )}

                <Button
                  type="button"
                  variant="outlined"
                  startIcon={<TaskAltRoundedIcon />}
                  onClick={handleUseRefinedRequest}
                  sx={{
                    alignSelf: { xs: 'stretch', sm: 'flex-start' },
                    borderRadius: 3,
                    color: '#FFD3A0',
                    borderColor: 'rgba(255, 211, 160, 0.58)',
                    '&:hover': {
                      borderColor: '#FFD3A0',
                      backgroundColor: 'rgba(255, 211, 160, 0.1)',
                    },
                  }}
                >
                  Use this request
                </Button>
              </Stack>
            </Box>
          )}

          {advancedView && (
            <Box sx={{ p: 2.5, borderRadius: 3, bgcolor: 'rgba(8, 11, 14, 0.78)', border: '1px solid rgba(79, 69, 58, 0.5)' }}>
              <Typography variant="subtitle2" sx={{ color: '#E2E2E3', mb: 1 }}>
                Advanced View
              </Typography>
              <Typography variant="body2" sx={{ color: 'rgba(226, 226, 227, 0.72)', mb: 1.25 }}>
                Technical request payload preview
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
                {JSON.stringify(structuredPreview, null, 2)}
              </Box>
            </Box>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default AICommandPanel;
