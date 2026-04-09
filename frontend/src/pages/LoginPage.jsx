/**
 * Authentication landing page for login and registration.
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Typography from '@mui/material/Typography';
import { useAuth } from '../context/AuthContext';
import { extractApiErrorMessage } from '../services/api';

const LOGIN_REQUIRED_MESSAGE = 'Enter a valid email and password to sign in.';
const REGISTER_REQUIRED_MESSAGE = 'Enter a valid email and password to create your account.';

const normalizeAuthError = (err, isRegisterMode) => {
  const friendlyMessage = extractApiErrorMessage(err, '');

  if (err?.response?.status === 422) {
    if (friendlyMessage && !/^request validation failed\.?$/i.test(friendlyMessage.trim())) {
      return friendlyMessage;
    }
    return isRegisterMode ? REGISTER_REQUIRED_MESSAGE : LOGIN_REQUIRED_MESSAGE;
  }

  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  return friendlyMessage || extractApiErrorMessage(err, isRegisterMode ? 'Registration failed' : 'Login failed');
};

const authFieldSx = {
  '& .MuiOutlinedInput-root': {
    borderRadius: 2.5,
    bgcolor: 'rgba(8, 11, 14, 0.78)',
    color: '#E2E2E3',
    '& fieldset': {
      borderColor: 'rgba(79, 69, 58, 0.5)',
    },
    '&:hover fieldset': {
      borderColor: 'rgba(240, 189, 127, 0.42)',
    },
    '&.Mui-focused fieldset': {
      borderColor: 'rgba(240, 189, 127, 0.8)',
      boxShadow: '0 0 0 1px rgba(240, 189, 127, 0.24)',
    },
  },
  '& .MuiInputLabel-root': {
    color: 'rgba(226, 226, 227, 0.72)',
  },
  '& .MuiInputLabel-root.Mui-focused': {
    color: '#FFD3A0',
  },
  '& input:-webkit-autofill': {
    WebkitTextFillColor: '#E2E2E3',
    WebkitBoxShadow: '0 0 0 100px rgba(8, 11, 14, 0.9) inset',
    transition: 'background-color 9999s ease-out 0s',
    caretColor: '#E2E2E3',
  },
  '& input:-webkit-autofill:hover': {
    WebkitTextFillColor: '#E2E2E3',
    WebkitBoxShadow: '0 0 0 100px rgba(8, 11, 14, 0.9) inset',
  },
  '& input:-webkit-autofill:focus': {
    WebkitTextFillColor: '#E2E2E3',
    WebkitBoxShadow: '0 0 0 100px rgba(8, 11, 14, 0.9) inset',
  },
};

const LoginPage = () => {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const isRegisterMode = mode === 'register';

  const handleModeChange = (_event, value) => {
    if (!value) {
      return;
    }

    setMode(value);
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    const normalizedEmail = email.trim();
    const normalizedPassword = password.trim();
    const normalizedConfirmPassword = confirmPassword.trim();

    if (!normalizedEmail || !normalizedPassword) {
      setError(isRegisterMode ? REGISTER_REQUIRED_MESSAGE : LOGIN_REQUIRED_MESSAGE);
      return;
    }

    if (isRegisterMode && !normalizedConfirmPassword) {
      setError('Confirm your password to create the account.');
      return;
    }

    if (isRegisterMode && normalizedPassword !== normalizedConfirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);

    try {
      const result = isRegisterMode
        ? await register({ email: normalizedEmail, password: normalizedPassword })
        : await login(normalizedEmail, normalizedPassword);

      if (!result.success) {
        setError(result.error || (isRegisterMode ? 'Registration failed' : 'Login failed'));
        return;
      }

      navigate('/dashboard');
    } catch (err) {
      setError(normalizeAuthError(err, isRegisterMode));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', px: 2, mt: { xs: 4, md: 8 } }}>
      <Card
        sx={{
          maxWidth: 460,
          width: '100%',
          borderRadius: 4,
          color: '#E2E2E3',
          border: '1px solid rgba(79, 69, 58, 0.6)',
          boxShadow: '0 24px 70px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
          background:
            'radial-gradient(circle at top center, rgba(255, 211, 160, 0.12), transparent 40%), rgba(28, 31, 35, 0.84)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
        }}
      >
        <CardContent sx={{ p: { xs: 3, md: 4 } }}>
          <Stack spacing={3}>
            <Box>
              <Typography variant="h4" component="h1" gutterBottom sx={{ color: '#F8F9FA' }}>
                {isRegisterMode ? 'Create your account' : 'Welcome back'}
              </Typography>
              <Typography sx={{ color: 'rgba(226, 226, 227, 0.76)' }}>
                {isRegisterMode
                  ? 'Create an account to start asking Smart Scraper for data in plain English.'
                  : 'Sign in to continue to your Smart Scraper workspace.'}
              </Typography>
            </Box>

            <ToggleButtonGroup
              value={mode}
              exclusive
              onChange={handleModeChange}
              fullWidth
              sx={{
                borderRadius: 2.5,
                bgcolor: 'rgba(8, 11, 14, 0.72)',
                border: '1px solid rgba(79, 69, 58, 0.5)',
                '& .MuiToggleButtonGroup-grouped': {
                  color: 'rgba(226, 226, 227, 0.88)',
                  borderColor: 'rgba(79, 69, 58, 0.35)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.12em',
                  fontWeight: 700,
                  py: 1.2,
                },
                '& .MuiToggleButtonGroup-grouped.Mui-selected': {
                  color: '#101215',
                  bgcolor: '#FFD3A0',
                  borderColor: 'rgba(255, 211, 160, 0.7)',
                  '&:hover': {
                    bgcolor: '#F0BD7F',
                  },
                },
              }}
            >
              <ToggleButton value="login">Login</ToggleButton>
              <ToggleButton value="register">Create account</ToggleButton>
            </ToggleButtonGroup>

            {error && (
              <Alert
                severity="error"
                sx={{
                  borderRadius: 2.5,
                  backgroundColor: 'rgba(255, 111, 145, 0.12)',
                  color: '#FBE8EE',
                  border: '1px solid rgba(255, 111, 145, 0.35)',
                  '& .MuiAlert-icon': {
                    color: '#FF6F91',
                  },
                }}
              >
                {error}
              </Alert>
            )}

            <form onSubmit={handleSubmit} noValidate>
              <TextField
                fullWidth
                label="Email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                margin="normal"
                required
                sx={authFieldSx}
              />
              <TextField
                fullWidth
                label="Password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                margin="normal"
                required
                sx={authFieldSx}
              />
              {isRegisterMode && (
                <TextField
                  fullWidth
                  label="Confirm password"
                  type={showPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  margin="normal"
                  required
                  sx={authFieldSx}
                />
              )}
              <FormControlLabel
                control={(
                  <Checkbox
                    checked={showPassword}
                    onChange={(event) => setShowPassword(event.target.checked)}
                    sx={{
                      color: 'rgba(226, 226, 227, 0.6)',
                      '&.Mui-checked': {
                        color: '#FFD3A0',
                      },
                    }}
                  />
                )}
                label="Show characters"
                sx={{
                  mt: 0.5,
                  mb: 0.5,
                  color: 'rgba(226, 226, 227, 0.76)',
                  '& .MuiFormControlLabel-label': {
                    fontSize: 14,
                  },
                }}
              />
              <Button
                type="submit"
                variant="contained"
                fullWidth
                sx={{
                  mt: 2,
                  py: 1.35,
                  borderRadius: 2.5,
                  fontWeight: 800,
                  letterSpacing: '0.09em',
                  textTransform: 'uppercase',
                  color: '#121415',
                  background: 'linear-gradient(135deg, #FFD3A0 0%, #E8B678 100%)',
                  boxShadow: 'inset 0 4px 12px rgba(255,255,255,0.15), 0 8px 30px rgba(240,189,127,0.25)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #FFD9AA 0%, #F0BD7F 100%)',
                    boxShadow: 'inset 0 4px 12px rgba(255,255,255,0.15), 0 10px 36px rgba(240,189,127,0.3)',
                  },
                  '&.Mui-disabled': {
                    color: 'rgba(18, 20, 21, 0.6)',
                    background: 'linear-gradient(135deg, rgba(255, 211, 160, 0.66) 0%, rgba(232, 182, 120, 0.66) 100%)',
                  },
                }}
                disabled={loading}
              >
                {loading
                  ? (isRegisterMode ? 'Creating account...' : 'Logging in...')
                  : (isRegisterMode ? 'Create account' : 'Login')}
              </Button>
            </form>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
};

export default LoginPage;
