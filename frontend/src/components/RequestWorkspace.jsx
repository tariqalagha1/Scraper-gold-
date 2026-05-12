import React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';

const inputSx = {
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
};

const RequestWorkspace = ({
  url,
  requestText,
  location,
  limit,
  maxPages,
  followPagination,
  requiresLogin,
  loginUrl,
  loginUsername,
  loginPassword,
  fieldsText,
  sourceType,
  onFieldChange,
  onRefine,
  onUseRefined,
  refining,
  assistantError,
  assistantMessage,
  refinedPrompt,
  recommendedType,
  readyToApply,
  clarifyingQuestions,
  followUpAnswers,
  onFollowUpAnswerChange,
  showGuidedInputHint = false,
  onRequestInputFocus,
  showAssistantHandoffHint = false,
  isOnboardingSampleInput = false,
}) => (
  <Card sx={{ borderRadius: 4, boxShadow: 'none', border: '1px solid rgba(79, 69, 58, 0.5)', bgcolor: 'rgba(28, 31, 35, 0.84)' }}>
    <CardContent sx={{ p: { xs: 3, md: 4 } }}>
      <Stack spacing={2.5}>
        <div>
          <Stack direction="row" spacing={1.25} alignItems="center">
            <AutoAwesomeIcon sx={{ color: '#FFD3A0' }} />
            <Typography variant="h5" sx={{ color: '#E2E2E3' }}>
              RequestWorkspace
            </Typography>
          </Stack>
          <Typography sx={{ color: 'rgba(226, 226, 227, 0.72)', mt: 1 }}>
            Step 1-2: Type a simple request, then let Request Assistant refine it.
          </Typography>
        </div>

        {assistantError && <Alert severity="error" sx={{ borderRadius: 3 }}>{assistantError}</Alert>}

        {showGuidedInputHint && (
          <Box
            sx={{
              borderRadius: 2,
              border: '1px solid rgba(255, 211, 160, 0.45)',
              backgroundColor: 'rgba(255, 211, 160, 0.06)',
              px: 1.5,
              py: 1.25,
            }}
            data-testid="guided-input-hint"
          >
            <Typography variant="body2" sx={{ color: '#F6D28F', fontWeight: 600 }}>
              Describe what you want to find
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(226, 226, 227, 0.72)' }}>
              We’ll structure your request automatically
            </Typography>
          </Box>
        )}

        <Box
          data-testid={showGuidedInputHint ? 'guided-input-highlight' : undefined}
          sx={
            showGuidedInputHint
              ? {
                  borderRadius: 3,
                  p: 0.5,
                  border: '1px solid rgba(255, 211, 160, 0.42)',
                  backgroundColor: 'rgba(255, 211, 160, 0.04)',
                }
              : undefined
          }
        >
          <TextField
            label="Simple request"
            placeholder="Find hospitals and collect name, contact number, and email"
            value={requestText}
            onChange={(event) => onFieldChange('requestText', event.target.value)}
            onFocus={onRequestInputFocus}
            multiline
            minRows={3}
            fullWidth
            sx={inputSx}
          />
        </Box>

        <TextField
          label="Website URL"
          placeholder="https://example.com"
          value={url}
          onChange={(event) => onFieldChange('url', event.target.value)}
          fullWidth
          sx={inputSx}
          helperText="Optional for query/location mode. Required to run a full scraping job."
        />

        <Grid container spacing={1.5}>
          <Grid item xs={12} md={4}>
            <TextField
              label="Location"
              placeholder="Saudi Arabia"
              value={location}
              onChange={(event) => onFieldChange('location', event.target.value)}
              fullWidth
              sx={inputSx}
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField
              label="Limit"
              type="number"
              value={limit}
              onChange={(event) => onFieldChange('limit', event.target.value)}
              fullWidth
              inputProps={{ min: 1, max: 500 }}
              sx={inputSx}
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField
              label="Max pages"
              type="number"
              value={maxPages}
              onChange={(event) => onFieldChange('maxPages', event.target.value)}
              fullWidth
              inputProps={{ min: 1, max: 1000 }}
              sx={inputSx}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              label="Source type (optional)"
              placeholder="directory"
              value={sourceType}
              onChange={(event) => onFieldChange('sourceType', event.target.value)}
              fullWidth
              sx={inputSx}
            />
          </Grid>
        </Grid>

        <FormControlLabel
          control={(
            <Checkbox
              checked={Boolean(followPagination)}
              onChange={(event) => onFieldChange('followPagination', event.target.checked)}
              sx={{
                color: '#9E8A73',
                '&.Mui-checked': {
                  color: '#FFD3A0',
                },
              }}
            />
          )}
          label="Follow pagination links"
          sx={{
            px: 1,
            py: 0.25,
            borderRadius: 1.5,
            border: '1.5px solid rgba(110, 92, 73, 0.78)',
            backgroundColor: 'rgba(8, 11, 14, 0.55)',
            color: '#E2E2E3',
            width: 'fit-content',
          }}
        />

        <FormControlLabel
          control={(
            <Checkbox
              checked={Boolean(requiresLogin)}
              onChange={(event) => onFieldChange('requiresLogin', event.target.checked)}
              sx={{
                color: '#9E8A73',
                '&.Mui-checked': {
                  color: '#FFD3A0',
                },
              }}
            />
          )}
          label="Website requires login"
          sx={{
            px: 1,
            py: 0.25,
            borderRadius: 1.5,
            border: '1.5px solid rgba(110, 92, 73, 0.78)',
            backgroundColor: 'rgba(8, 11, 14, 0.55)',
            color: '#E2E2E3',
            width: 'fit-content',
          }}
        />

        {requiresLogin && (
          <Grid container spacing={1.5}>
            <Grid item xs={12}>
              <TextField
                label="Login URL"
                placeholder="https://example.com/login"
                value={loginUrl}
                onChange={(event) => onFieldChange('loginUrl', event.target.value)}
                fullWidth
                sx={inputSx}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="Username / Email"
                value={loginUsername}
                onChange={(event) => onFieldChange('loginUsername', event.target.value)}
                fullWidth
                sx={inputSx}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="Password"
                type="password"
                value={loginPassword}
                onChange={(event) => onFieldChange('loginPassword', event.target.value)}
                fullWidth
                sx={inputSx}
              />
            </Grid>
          </Grid>
        )}

        <TextField
          label="Fields"
          placeholder="name, contact, email"
          value={fieldsText}
          onChange={(event) => onFieldChange('fieldsText', event.target.value)}
          fullWidth
          sx={inputSx}
          helperText="Comma-separated fields"
        />

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25}>
            <Button
              type="button"
              variant="outlined"
            disabled={refining}
            onClick={onRefine}
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
              {refining ? 'Refining...' : 'Refine Request'}
            </Button>
          </Stack>

          {showAssistantHandoffHint && (
            <Box
              sx={{
                borderRadius: 2,
                border: '1px solid rgba(255, 211, 160, 0.32)',
                backgroundColor: 'rgba(255, 211, 160, 0.04)',
                px: 1.5,
                py: 1.1,
              }}
              data-testid="assistant-handoff-hint"
            >
              <Typography variant="body2" sx={{ color: '#F6D28F', fontWeight: 600 }}>
                Make your request smarter before running
              </Typography>
              {isOnboardingSampleInput && (
                <Typography
                  variant="caption"
                  sx={{ color: 'rgba(226, 226, 227, 0.72)', display: 'block', mt: 0.35 }}
                >
                  Recommended for this sample request.
                </Typography>
              )}
            </Box>
          )}

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
                  label={readyToApply ? 'Ready to run' : 'Needs clarification'}
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
                    Clarifying questions
                  </Typography>
                  {clarifyingQuestions.map((question) => (
                    <TextField
                      key={question}
                      label={question}
                      value={followUpAnswers[question] || ''}
                      onChange={(event) => onFollowUpAnswerChange(question, event.target.value)}
                      fullWidth
                      sx={inputSx}
                    />
                  ))}
                </Stack>
              )}

              <Typography
                variant="body2"
                sx={{ color: '#F6D28F' }}
                data-testid="use-request-guidance"
              >
                This looks good. Use it to prepare your search.
              </Typography>

              <Button
                type="button"
                variant="contained"
                onClick={onUseRefined}
                data-testid="use-this-request-button"
                sx={{
                  alignSelf: { xs: 'stretch', sm: 'flex-start' },
                  borderRadius: 3,
                  px: 2.25,
                  background: 'linear-gradient(135deg, #FFD3A0 0%, #E8B678 100%)',
                  color: '#121415',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #FFD9AA 0%, #F0BD7F 100%)',
                  },
                }}
              >
                Use This Request
              </Button>
            </Stack>
          </Box>
        )}
      </Stack>
    </CardContent>
  </Card>
);

export default RequestWorkspace;
