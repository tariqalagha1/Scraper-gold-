import React, { useEffect, useMemo, useState } from 'react';
import api, { API_KEY_HEADER_NAME, extractApiErrorMessage } from '../services/api';
import { formatDate } from '../utils/helpers';
import { PageHeader, PrimaryButton, Section } from '../components/ui';

const API_KEY_NAME_MAX_LENGTH = 120;
const focusClass = 'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950';

const resolveIntegrationBaseUrl = () => {
  const configured = (process.env.REACT_APP_API_URL || '').trim();
  if (configured) return configured;
  if (typeof window !== 'undefined') return `${window.location.origin}/api/v1`;
  return '/api/v1';
};

const ApiKeysPage = () => {
  const [apiKeys, setApiKeys] = useState([]);
  const [name, setName] = useState('');
  const [createdKey, setCreatedKey] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [revokingId, setRevokingId] = useState('');

  const baseUrl = useMemo(resolveIntegrationBaseUrl, []);

  const loadApiKeys = async () => {
    try {
      setLoading(true);
      const keys = await api.getApiKeys();
      setApiKeys(keys || []);
      setError('');
    } catch (loadError) {
      setError(extractApiErrorMessage(loadError, 'Could not load API keys.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApiKeys();
  }, []);

  const handleCreate = async () => {
    const normalizedName = String(name || '').trim();
    if (!normalizedName) {
      setError('Key name is required.');
      return;
    }
    if (normalizedName.length > API_KEY_NAME_MAX_LENGTH) {
      setError(`Key name must be ${API_KEY_NAME_MAX_LENGTH} characters or fewer.`);
      return;
    }

    try {
      setCreating(true);
      const created = await api.createApiKey({ name: normalizedName });
      const raw = created.api_key || created.key || '';
      if (!raw) {
        throw new Error('Created key was not returned by backend.');
      }

      setCreatedKey(raw);
      setNotice('API key created. Copy it now; this is the only full display.');
      setName('');
      setError('');
      await loadApiKeys();
    } catch (createError) {
      setError(extractApiErrorMessage(createError, 'Could not create API key.'));
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (apiKeyId) => {
    if (!apiKeyId || revokingId) return;

    const confirmed = typeof window === 'undefined' || window.confirm('Revoke this API key?');
    if (!confirmed) return;

    try {
      setRevokingId(apiKeyId);
      await api.deleteApiKey(apiKeyId);
      setNotice('API key revoked.');
      setError('');
      await loadApiKeys();
    } catch (revokeError) {
      setError(extractApiErrorMessage(revokeError, 'Could not revoke API key.'));
    } finally {
      setRevokingId('');
    }
  };

  const copyToClipboard = async (value, successMessage) => {
    if (!navigator.clipboard || !value) return;
    await navigator.clipboard.writeText(value);
    setNotice(successMessage);
    window.setTimeout(() => setNotice(''), 1800);
  };

  const curlSnippet = `curl -X POST "${baseUrl}/scrape" \\
  -H "Content-Type: application/json" \\
  -H "${API_KEY_HEADER_NAME}: ss_your_key_here" \\
  -d '{"query":"hospitals in Riyadh","fields":["name","phone","email"],"limit":20}'`;

  const jsSnippet = `const response = await fetch("${baseUrl}/scrape", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "${API_KEY_HEADER_NAME}": "ss_your_key_here"
  },
  body: JSON.stringify({
    query: "hospitals in Riyadh",
    fields: ["name", "phone", "email"],
    limit: 20
  })
});
const data = await response.json();`;

  const pythonSnippet = `import requests

response = requests.post(
    "${baseUrl}/scrape",
    headers={
        "Content-Type": "application/json",
        "${API_KEY_HEADER_NAME}": "ss_your_key_here",
    },
    json={
        "query": "hospitals in Riyadh",
        "fields": ["name", "phone", "email"],
        "limit": 20,
    },
)
print(response.json())`;

  return (
    <section className="space-y-4">
      <PageHeader
        title="API Keys"
        description="Create, copy, and revoke API keys for external integrations."
      />

      {(error || notice) && (
        <div
          className={`rounded-xl border px-3 py-2 text-sm ${
            error
              ? 'border-red-400/30 bg-red-400/10 text-red-200'
              : 'border-emerald-500/25 bg-emerald-500/10 text-emerald-200'
          }`}
          role={error ? 'alert' : 'status'}
        >
          {error || notice}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Create API key" description="Use one key per app or script so you can revoke safely later.">
          <div className="space-y-3">
            <div className="space-y-1">
              <label htmlFor="api-key-name" className="text-sm text-slate-400">
                Key name
              </label>
              <input
                id="api-key-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                maxLength={API_KEY_NAME_MAX_LENGTH}
                placeholder="Example: BI sync script"
                className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 ${focusClass}`}
              />
            </div>

            <p className="text-xs text-slate-500">{String(name || '').trim().length}/{API_KEY_NAME_MAX_LENGTH}</p>

            <PrimaryButton type="button" onClick={handleCreate} disabled={creating}>
              {creating ? 'Creating...' : 'Create key'}
            </PrimaryButton>

            {createdKey && (
              <div className="rounded-xl border border-white/10 bg-slate-900 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-500">New key (shown once)</p>
                <code className="mt-2 block break-all text-sm text-slate-200">{createdKey}</code>
                <button
                  type="button"
                  onClick={() => copyToClipboard(createdKey, 'API key copied.')}
                  className={`mt-2 rounded-lg border border-white/10 bg-slate-800 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-500 ${focusClass}`}
                >
                  Copy key
                </button>
              </div>
            )}
          </div>
        </Section>

        <Section title="Your keys" description="Revoke any key immediately if it is no longer needed.">
          {loading ? (
            <p className="text-sm text-slate-400">Loading API keys...</p>
          ) : apiKeys.length === 0 ? (
            <p className="text-sm text-slate-400">No API keys yet.</p>
          ) : (
            <ul className="space-y-2">
              {apiKeys.map((apiKey) => (
                <li key={apiKey.id} className="rounded-xl border border-white/10 bg-slate-900 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-slate-100">{apiKey.name}</p>
                      <p className="text-xs text-slate-400">{apiKey.key_preview}</p>
                      <p className="text-xs text-slate-500">Created {formatDate(apiKey.created_at)}</p>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleRevoke(apiKey.id)}
                      disabled={revokingId === apiKey.id}
                      className={`rounded-lg border border-red-400/30 bg-red-400/10 px-3 py-1 text-xs text-red-200 transition hover:border-red-300 disabled:cursor-not-allowed disabled:opacity-60 ${focusClass}`}
                    >
                      {revokingId === apiKey.id ? 'Revoking...' : 'Revoke'}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Code snippets" description="Use these examples with your base URL and API key.">
        <p className="text-sm text-slate-400">
          Base URL: <span className="text-slate-200">{baseUrl}</span> • Auth header:{' '}
          <span className="text-slate-200">{API_KEY_HEADER_NAME}</span>
        </p>

        <div className="mt-3 grid gap-3 lg:grid-cols-3">
          <div className="rounded-xl border border-white/10 bg-slate-900 p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-medium text-slate-200">curl</p>
              <button
                type="button"
                onClick={() => copyToClipboard(curlSnippet, 'curl snippet copied.')}
                className={`text-xs text-slate-400 hover:text-slate-200 ${focusClass}`}
              >
                Copy
              </button>
            </div>
            <pre className="max-h-72 overflow-auto text-xs text-slate-300">{curlSnippet}</pre>
          </div>

          <div className="rounded-xl border border-white/10 bg-slate-900 p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-medium text-slate-200">JavaScript</p>
              <button
                type="button"
                onClick={() => copyToClipboard(jsSnippet, 'JavaScript snippet copied.')}
                className={`text-xs text-slate-400 hover:text-slate-200 ${focusClass}`}
              >
                Copy
              </button>
            </div>
            <pre className="max-h-72 overflow-auto text-xs text-slate-300">{jsSnippet}</pre>
          </div>

          <div className="rounded-xl border border-white/10 bg-slate-900 p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-medium text-slate-200">Python</p>
              <button
                type="button"
                onClick={() => copyToClipboard(pythonSnippet, 'Python snippet copied.')}
                className={`text-xs text-slate-400 hover:text-slate-200 ${focusClass}`}
              >
                Copy
              </button>
            </div>
            <pre className="max-h-72 overflow-auto text-xs text-slate-300">{pythonSnippet}</pre>
          </div>
        </div>
      </Section>
    </section>
  );
};

export default ApiKeysPage;
