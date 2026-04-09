/**
 * Login form component for target site credentials.
 */
import React, { useState } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';

const LoginForm = ({ credentials, onChange, requiresLogin, onRequiresLoginChange }) => {
  const [showPassword, setShowPassword] = useState(false);
  const fieldBorderColor = 'rgba(226, 188, 139, 0.6)';
  const fieldBackground = 'rgba(6, 9, 12, 0.72)';

  const handleChange = (field) => (e) => {
    onChange({ ...credentials, [field]: e.target.value });
  };

  return (
    <Box sx={{ mt: 1 }}>
      <Typography variant="h6" gutterBottom>
        Target Site Login (Optional)
      </Typography>
      <Typography variant="body2" sx={{ color: 'rgba(226,226,227,0.74)', mb: 1.5 }}>
        Enable this only if the target website requires authentication.
      </Typography>
      <FormControlLabel
        control={
          <Checkbox
            checked={requiresLogin}
            onChange={(e) => onRequiresLoginChange(e.target.checked)}
            sx={{
              color: '#9E8A73',
              '&.Mui-checked': {
                color: '#FFD3A0',
              },
            }}
          />
        }
        label="Site requires login"
        sx={{
          px: 1,
          py: 0.25,
          borderRadius: 1.5,
          border: '1.5px solid rgba(110, 92, 73, 0.78)',
          backgroundColor: 'rgba(8, 11, 14, 0.55)',
          color: '#E2E2E3',
        }}
      />
      {requiresLogin && (
        <Box
          sx={{
            mt: 1.5,
            p: 2,
            borderRadius: 2,
            border: '1px solid rgba(110, 92, 73, 0.75)',
            background: 'rgba(9, 11, 14, 0.45)',
          }}
        >
          <TextField
            fullWidth
            label="Login URL"
            value={credentials.loginUrl || ''}
            onChange={handleChange('loginUrl')}
            placeholder="https://example.com/account/login"
            InputLabelProps={{ shrink: true }}
            sx={{
              mb: 2,
              '& .MuiInputLabel-root': {
                color: 'rgba(226, 226, 227, 0.85)',
              },
              '& .MuiOutlinedInput-root': {
                backgroundColor: fieldBackground,
                '& input': {
                  color: '#E2E2E3',
                },
                '& fieldset': {
                  borderColor: fieldBorderColor,
                  borderWidth: 1.5,
                },
                '&:hover fieldset': {
                  borderColor: '#E2BC8B',
                },
                '&.Mui-focused fieldset': {
                  borderColor: '#E2BC8B',
                  borderWidth: 2,
                },
              },
            }}
          />
          <Box
            sx={{
              display: 'grid',
              gap: 2,
              gridTemplateColumns: {
                xs: '1fr',
                sm: '1fr 1fr',
              },
            }}
          >
            <TextField
              fullWidth
              label="Username / Email"
              value={credentials.username || ''}
              onChange={handleChange('username')}
              InputLabelProps={{ shrink: true }}
              sx={{
                '& .MuiInputLabel-root': {
                  color: 'rgba(226, 226, 227, 0.85)',
                },
                '& .MuiOutlinedInput-root': {
                  backgroundColor: fieldBackground,
                  '& input': {
                    color: '#E2E2E3',
                  },
                  '& fieldset': {
                    borderColor: fieldBorderColor,
                    borderWidth: 1.5,
                  },
                  '&:hover fieldset': {
                    borderColor: '#E2BC8B',
                  },
                  '&.Mui-focused fieldset': {
                    borderColor: '#E2BC8B',
                    borderWidth: 2,
                  },
                },
              }}
            />
            <TextField
              fullWidth
              type={showPassword ? 'text' : 'password'}
              label="Password"
              value={credentials.password || ''}
              onChange={handleChange('password')}
              InputLabelProps={{ shrink: true }}
              sx={{
                '& .MuiInputLabel-root': {
                  color: 'rgba(226, 226, 227, 0.85)',
                },
                '& .MuiOutlinedInput-root': {
                  backgroundColor: fieldBackground,
                  '& input': {
                    color: '#E2E2E3',
                  },
                  '& fieldset': {
                    borderColor: fieldBorderColor,
                    borderWidth: 1.5,
                  },
                  '&:hover fieldset': {
                    borderColor: '#E2BC8B',
                  },
                  '&.Mui-focused fieldset': {
                    borderColor: '#E2BC8B',
                    borderWidth: 2,
                  },
                },
              }}
            />
          </Box>
          <Box
            sx={{
              mt: 1.5,
              px: 1.25,
              py: 0.25,
              borderRadius: 1.5,
              border: `1.5px solid ${fieldBorderColor}`,
              backgroundColor: fieldBackground,
              display: 'inline-flex',
            }}
          >
            <FormControlLabel
              control={(
                <Checkbox
                  checked={showPassword}
                  onChange={(event) => setShowPassword(event.target.checked)}
                  sx={{
                    color: '#9E8A73',
                    '&.Mui-checked': {
                      color: '#FFD3A0',
                    },
                  }}
                />
              )}
              label="Show password"
              sx={{ m: 0, color: '#E2E2E3' }}
            />
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default LoginForm;
