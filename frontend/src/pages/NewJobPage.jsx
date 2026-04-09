/**
 * New job page with step-by-step wizard.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Alert from '@mui/material/Alert';
import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import { buildIntentTitle, interpretCommand, saveRecentRequest } from '../assistant/orchestrator';
import StepWizard from '../components/StepWizard';
import DataTypeSelector from '../components/DataTypeSelector';
import LoginForm from '../components/LoginForm';
import api from '../services/api';
import { consumeLandingExtractionIntent } from '../utils/extractionIntent';

const MAX_PROMPT_LENGTH = 2000;
const warmGold = '#E2BC8B';
const warmGoldStrong = '#FFD3A0';
const warmBorder = 'rgba(110, 92, 73, 0.78)';
const fieldBackground = 'rgba(6, 9, 12, 0.72)';
const warmTextFieldSx = {
  '& .MuiInputLabel-root': {
    color: 'rgba(226, 226, 227, 0.85)',
  },
  '& .MuiInputLabel-root.Mui-focused': {
    color: warmGoldStrong,
  },
    '& .MuiOutlinedInput-root': {
      backgroundColor: fieldBackground,
      '& input': {
        color: '#E2E2E3',
        '&::placeholder': {
          color: 'rgba(226,226,227,0.45)',
          opacity: 1,
        },
      },
      '& textarea': {
        color: '#E2E2E3',
        '&::placeholder': {
          color: 'rgba(226,226,227,0.45)',
          opacity: 1,
        },
      },
    '& fieldset': {
      borderColor: warmBorder,
      borderWidth: 1.5,
    },
    '&:hover fieldset': {
      borderColor: warmGold,
    },
    '&.Mui-focused fieldset': {
      borderColor: warmGoldStrong,
      borderWidth: 2,
    },
  },
  '& .MuiFormHelperText-root': {
    color: 'rgba(226,226,227,0.65)',
  },
};

const isValidHttpUrl = (value) => {
  try {
    const parsed = new URL(value);
    return ['http:', 'https:'].includes(parsed.protocol);
  } catch (error) {
    return false;
  }
};

const fullCoverageMarkers = [
  'all pages',
  'all page',
  'entire pages',
  'entire page',
  'intire pages',
  'full pages',
  'every page',
  'all records',
  'all patients',
  'complete data',
];

const shouldBoostPageBudget = (value) => {
  const promptValue = String(value || '').trim().toLowerCase();
  if (!promptValue) {
    return false;
  }
  return fullCoverageMarkers.some((marker) => promptValue.includes(marker));
};

const NewJobPage = () => {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [prompt, setPrompt] = useState('');
  const [scrapeType, setScrapeType] = useState('general');
  const [maxPages, setMaxPages] = useState(10);
  const [followPagination, setFollowPagination] = useState(true);
  const [requiresLogin, setRequiresLogin] = useState(false);
  const [credentials, setCredentials] = useState({});
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const intent = consumeLandingExtractionIntent();
    if (!intent) {
      return;
    }

    const preview = interpretCommand({
      url: intent.url,
      prompt: intent.prompt,
    });

    setUrl(intent.url);
    setPrompt(intent.prompt || '');
    setScrapeType(intent.scrape_type || preview.scrape_type || 'general');
    setMaxPages(intent.max_pages || 10);
    setFollowPagination(intent.follow_pagination ?? true);
    setRequiresLogin(intent.requiresLogin);
    setCredentials({
      loginUrl: intent.login_url || '',
      username: intent.login_username || '',
      password: intent.login_password || '',
    });
  }, []);

  const validateSubmission = () => {
    const trimmedUrl = url.trim();
    const trimmedPrompt = prompt.trim();
    const trimmedLoginUrl = (credentials.loginUrl || '').trim();
    const trimmedUsername = (credentials.username || '').trim();
    const trimmedPassword = (credentials.password || '').trim();

    if (!trimmedUrl) {
      return 'Enter a target URL before creating the job.';
    }
    if (!isValidHttpUrl(trimmedUrl)) {
      return 'Enter a valid http:// or https:// URL.';
    }
    if (trimmedPrompt.length > MAX_PROMPT_LENGTH) {
      return `Prompt must be ${MAX_PROMPT_LENGTH} characters or fewer.`;
    }
    if (requiresLogin) {
      if (!trimmedLoginUrl || !trimmedUsername || !trimmedPassword) {
        return 'Enter the login URL, username, and password for protected pages.';
      }
      if (!isValidHttpUrl(trimmedLoginUrl)) {
        return 'Enter a valid login URL for the protected site.';
      }
    }
    return '';
  };

  const handleSubmit = async () => {
    const validationError = validateSubmission();
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setSubmitting(true);
      setError('');
      setInfo('');
      const trimmedUrl = url.trim();
      const trimmedPrompt = prompt.trim();
      const inferredType = interpretCommand({
        url: trimmedUrl,
        prompt: trimmedPrompt,
      }).scrape_type;
      const effectiveScrapeType = scrapeType === 'excel' && inferredType === 'structured'
        ? 'structured'
        : scrapeType;
      const effectiveMaxPages = followPagination && maxPages <= 10 && shouldBoostPageBudget(trimmedPrompt)
        ? 1000
        : maxPages;
      const infoParts = [];

      if (effectiveScrapeType !== scrapeType) {
        infoParts.push('Prompt intent matched Structured Data. We switched extraction type to Structured so fields like name/mobile/id are captured correctly. You can still export as Excel.');
      }
      if (effectiveMaxPages !== maxPages) {
        infoParts.push('Prompt requested full pagination coverage. We raised Maximum pages to 1000 for this run.');
      }
      if (infoParts.length > 0) {
        setInfo(infoParts.join(' '));
      }

      const createdJob = await api.createJob({
        url: trimmedUrl,
        prompt: trimmedPrompt || null,
        login_url: requiresLogin ? credentials.loginUrl.trim() || null : null,
        login_username: requiresLogin ? credentials.username.trim() || null : null,
        login_password: requiresLogin ? credentials.password.trim() || null : null,
        scrape_type: effectiveScrapeType,
        max_pages: effectiveMaxPages,
        follow_pagination: followPagination,
      });
      await api.startJobRun(createdJob.id);

      if (trimmedUrl) {
        saveRecentRequest({
          url: trimmedUrl,
          prompt: trimmedPrompt,
          scrape_type: effectiveScrapeType,
          max_pages: effectiveMaxPages,
          follow_pagination: followPagination,
          title: buildIntentTitle(trimmedPrompt, trimmedUrl),
        });
      }

      navigate(`/jobs/${createdJob.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create job');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Create New Scraping Job</Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {info && (
        <Alert
          severity="info"
          sx={{
            mb: 2,
            color: '#E2E2E3',
            border: `1px solid ${warmBorder}`,
            backgroundColor: 'rgba(36, 30, 22, 0.52)',
            '& .MuiAlert-icon': { color: warmGoldStrong },
          }}
        >
          {info}
        </Alert>
      )}
      {submitting && (
        <Alert
          severity="info"
          sx={{
            mb: 2,
            color: '#E2E2E3',
            border: `1px solid ${warmBorder}`,
            backgroundColor: 'rgba(36, 30, 22, 0.52)',
            '& .MuiAlert-icon': { color: warmGoldStrong },
          }}
        >
          Creating the job and starting the first run...
        </Alert>
      )}
      <StepWizard
        onSubmit={handleSubmit}
        submitLabel="Create Job & Start Run"
        submittingLabel="Creating Job & Starting Run..."
        isSubmitting={submitting}
      >
        {/* Step 1: Enter URL */}
        <Box>
          <Typography variant="h6" gutterBottom>Enter Target URL</Typography>
          <TextField
            fullWidth
            label="URL to scrape"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://books.toscrape.com/catalogue/category/books/travel_2/index.html"
            InputLabelProps={{ shrink: true }}
            sx={warmTextFieldSx}
          />
          <TextField
            fullWidth
            multiline
            minRows={3}
            label="What should we extract?"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Extract product titles, prices, and availability"
            InputLabelProps={{ shrink: true }}
            sx={{ ...warmTextFieldSx, mt: 2 }}
            helperText={`${prompt.trim().length}/${MAX_PROMPT_LENGTH}`}
            error={prompt.trim().length > MAX_PROMPT_LENGTH}
          />
        </Box>

        {/* Step 2: Select Data Type */}
        <DataTypeSelector value={scrapeType} onChange={setScrapeType} />

        {/* Step 3: Configure Options */}
        <Box>
          <Typography variant="h6" gutterBottom>Configure Options</Typography>
          <TextField
            fullWidth
            type="number"
            label="Maximum pages"
            value={maxPages}
            onChange={(event) => {
              const nextValue = Number(event.target.value);
              setMaxPages(Number.isFinite(nextValue) ? Math.max(1, Math.min(1000, nextValue)) : 10);
            }}
            inputProps={{ min: 1, max: 1000 }}
            InputLabelProps={{ shrink: true }}
            sx={{ ...warmTextFieldSx, mb: 2 }}
          />
          <FormControlLabel
            control={(
              <Checkbox
                checked={followPagination}
                onChange={(event) => setFollowPagination(event.target.checked)}
                sx={{
                  color: '#9E8A73',
                  '&.Mui-checked': {
                    color: warmGoldStrong,
                  },
                }}
              />
            )}
            label="Follow pagination links"
            sx={{
              mb: 2,
              px: 1,
              py: 0.25,
              borderRadius: 1.5,
              border: `1.5px solid ${warmBorder}`,
              backgroundColor: 'rgba(8, 11, 14, 0.55)',
            }}
          />
          <LoginForm
            credentials={credentials}
            onChange={setCredentials}
            requiresLogin={requiresLogin}
            onRequiresLoginChange={setRequiresLogin}
          />
        </Box>

        {/* Step 4: Review */}
        <Box>
          <Typography variant="h6" gutterBottom>Review Your Job</Typography>
          <Typography><strong>URL:</strong> {url}</Typography>
          {prompt && <Typography><strong>Request:</strong> {prompt}</Typography>}
          <Typography><strong>Data Type:</strong> {scrapeType}</Typography>
          <Typography><strong>Maximum Pages:</strong> {maxPages}</Typography>
          <Typography><strong>Follow Pagination:</strong> {followPagination ? 'Yes' : 'No'}</Typography>
          <Typography><strong>Requires Login:</strong> {requiresLogin ? 'Yes' : 'No'}</Typography>
        </Box>
      </StepWizard>
    </Box>
  );
};

export default NewJobPage;
