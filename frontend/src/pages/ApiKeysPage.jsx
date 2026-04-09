import React, { useEffect, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import api from '../services/api';
import { formatDate } from '../utils/helpers';

const ApiKeysPage = () => {
  const [apiKeys, setApiKeys] = useState([]);
  const [name, setName] = useState('');
  const [createdKey, setCreatedKey] = useState('');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  const loadApiKeys = async () => {
    try {
      setApiKeys(await api.getApiKeys());
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'We could not load your API keys.');
    }
  };

  useEffect(() => {
    loadApiKeys();
  }, []);

  const handleCreate = async () => {
    try {
      setError('');
      const created = await api.createApiKey({ name: name.trim() || 'Default key' });
      setCreatedKey(created.api_key || created.key || '');
      setCopied(false);
      setName('');
      await loadApiKeys();
    } catch (err) {
      setError(err.response?.data?.detail || 'We could not create that API key.');
    }
  };

  const handleDelete = async (apiKeyId) => {
    try {
      setError('');
      await api.deleteApiKey(apiKeyId);
      await loadApiKeys();
    } catch (err) {
      setError(err.response?.data?.detail || 'We could not delete that API key.');
    }
  };

  const handleCopy = async () => {
    if (!createdKey || !navigator.clipboard) {
      return;
    }

    await navigator.clipboard.writeText(createdKey);
    setCopied(true);
  };

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h3" gutterBottom>
          API Keys
        </Typography>
        <Typography color="text.secondary">
          API keys let your own tools connect to Smart Scraper. Treat them like passwords and store them somewhere safe.
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}
      {createdKey && (
        <Alert severity="success">
          Here is your new API key. This is the only time we will show it in full: <strong>{createdKey}</strong>
        </Alert>
      )}

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Card sx={{ borderRadius: 4, height: '100%' }}>
            <CardContent>
              <Typography variant="overline">Active Keys</Typography>
              <Typography variant="h4">{apiKeys.length}</Typography>
              <Typography color="text.secondary">Keys currently available in your account</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={8}>
          <Card sx={{ borderRadius: 4, height: '100%' }}>
            <CardContent>
              <Stack spacing={1}>
                <Typography variant="h6">How to use API keys</Typography>
                <Typography color="text.secondary">
                  Create one key per script, team, or integration so it is easy to manage access later.
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  <Chip label="Shown once" size="small" variant="outlined" />
                  <Chip label="Store safely" size="small" variant="outlined" />
                  <Chip label="Delete when unused" size="small" variant="outlined" />
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card sx={{ borderRadius: 4 }}>
        <CardContent>
          <Stack spacing={2}>
            <Typography variant="h6">Create a new key</Typography>
            <TextField
              label="Key name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Example: Reporting script"
              fullWidth
            />
            <Button variant="contained" onClick={handleCreate}>
              Create Key
            </Button>
            {createdKey && (
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ xs: 'flex-start', md: 'center' }}>
                <Button variant="outlined" onClick={handleCopy}>
                  {copied ? 'Copied' : 'Copy Key'}
                </Button>
                <Typography variant="body2" color="text.secondary">
                  Save this key somewhere secure before leaving the page.
                </Typography>
              </Stack>
            )}
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ borderRadius: 4 }}>
        <CardContent>
          <Stack spacing={2}>
            <Typography variant="h6">Your keys</Typography>
            {apiKeys.length === 0 ? (
              <Typography color="text.secondary">No API keys yet.</Typography>
            ) : (
              apiKeys.map((apiKey) => (
                <Card key={apiKey.id} variant="outlined" sx={{ borderRadius: 3 }}>
                  <CardContent sx={{ '&:last-child': { pb: 2 } }}>
                    <Stack
                      direction={{ xs: 'column', md: 'row' }}
                      spacing={1.5}
                      justifyContent="space-between"
                      alignItems={{ xs: 'flex-start', md: 'center' }}
                    >
                      <Box>
                        <Typography variant="subtitle1">{apiKey.name}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          Preview: {apiKey.key_preview}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Created {formatDate(apiKey.created_at)}
                        </Typography>
                      </Box>

                      <Button color="error" variant="outlined" onClick={() => handleDelete(apiKey.id)}>
                        Delete
                      </Button>
                    </Stack>
                  </CardContent>
                </Card>
              ))
            )}
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
};

export default ApiKeysPage;
