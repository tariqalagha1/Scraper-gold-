import React, { useEffect, useMemo, useState } from 'react';
import SectionHeader from '../components/SectionHeader';
import StatusBadge from '../components/StatusBadge';
import api from '../services/api';

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'serper', label: 'Serper' },
  { value: 'gemini', label: 'Gemini' },
];

const AiIntegrationsPage = () => {
  const [provider, setProvider] = useState('openai');
  const [apiKey, setApiKey] = useState('');
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState({ type: '', message: '' });

  useEffect(() => {
    loadCredentials();
  }, []);

  const loadCredentials = async () => {
    try {
      setLoading(true);
      const items = await api.getCredentials();
      setCredentials(items);
      setNotice({ type: '', message: '' });
    } catch (error) {
      setNotice({ type: 'error', message: 'Could not load saved provider credentials.' });
    } finally {
      setLoading(false);
    }
  };

  const currentCredential = useMemo(
    () => credentials.find((item) => item.provider === provider) || null,
    [credentials, provider]
  );

  const handleSave = async () => {
    if (!apiKey.trim()) {
      setNotice({ type: 'error', message: 'Enter a provider key before saving.' });
      return;
    }

    try {
      setSaving(true);
      const saved = await api.saveCredential({ provider, api_key: apiKey });
      setCredentials((previous) => {
        const remaining = previous.filter((item) => item.provider !== saved.provider);
        return [...remaining, saved].sort((left, right) => left.provider.localeCompare(right.provider));
      });
      setApiKey('');
      setNotice({ type: 'success', message: `${provider} key saved securely.` });
    } catch (error) {
      setNotice({ type: 'error', message: error.response?.data?.detail || 'Could not save provider key.' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (targetProvider) => {
    try {
      await api.deleteCredential(targetProvider);
      setCredentials((previous) => previous.filter((item) => item.provider !== targetProvider));
      if (provider === targetProvider) {
        setApiKey('');
      }
      setNotice({ type: 'success', message: `${targetProvider} key deleted.` });
    } catch (error) {
      setNotice({ type: 'error', message: error.response?.data?.detail || 'Could not delete provider key.' });
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 lg:px-8">
      <SectionHeader
        eyebrow="AgentCore Integration"
        title="AI Integrations"
        description="Provider keys are encrypted in the backend, never returned raw, and injected into backend execution only."
      />

      {notice.message && (
        <div
          className={`mt-8 rounded-3xl border px-5 py-4 text-sm ${
            notice.type === 'error'
              ? 'border-danger/30 bg-danger/10 text-danger'
              : 'border-success/30 bg-success/10 text-success'
          }`}
        >
          {notice.message}
        </div>
      )}

      <div className="mt-10 grid gap-8 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="rounded-[28px] border border-white/10 bg-surface p-6 shadow-glow">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent">API Keys</p>
          <h3 className="mt-3 text-2xl font-semibold text-textMain">Connect providers</h3>
          <p className="mt-3 text-sm leading-6 text-textMuted">
            Add or update one provider key at a time. The raw value is accepted once, encrypted in the backend, and never shown again.
          </p>

          <div className="mt-6 space-y-4">
            <div>
              <label className="mb-2 block text-sm text-textMuted">Provider</label>
              <select
                value={provider}
                onChange={(event) => setProvider(event.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-bg px-4 py-3 text-sm text-textMain outline-none focus:border-accent/40"
              >
                {PROVIDERS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-2 block text-sm text-textMuted">API Key</label>
              <input
                type="password"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder="Paste provider key"
                className="w-full rounded-2xl border border-white/10 bg-bg px-4 py-3 text-sm text-textMain outline-none placeholder:text-textMuted/60 focus:border-accent/40"
              />
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                disabled={saving}
                onClick={handleSave}
                className="rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-bg transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving ? 'Saving...' : currentCredential ? 'Update Key' : 'Add Key'}
              </button>
              {currentCredential && (
                <button
                  type="button"
                  onClick={() => handleDelete(provider)}
                  className="rounded-2xl border border-white/10 px-5 py-3 text-sm text-textMuted transition hover:border-danger/30 hover:text-danger"
                >
                  Delete Key
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="rounded-[28px] border border-white/10 bg-surface p-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent">Providers</p>
              <h3 className="mt-3 text-2xl font-semibold text-textMain">Stored integrations</h3>
            </div>
            <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-textMuted">
              {loading ? 'Loading...' : `${credentials.length} configured`}
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {credentials.map((item) => (
              <div key={item.provider} className="rounded-[24px] border border-white/10 bg-bg/60 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h4 className="text-lg font-semibold capitalize text-textMain">{item.provider}</h4>
                    <p className="mt-2 text-sm text-textMuted">Masked key: {item.key_mask}</p>
                    <p className="mt-2 text-xs text-textMuted">
                      Stored {new Date(item.created_at).toLocaleString()}
                    </p>
                  </div>
                  <StatusBadge status="success">stored</StatusBadge>
                </div>
              </div>
            ))}
            {!loading && credentials.length === 0 && (
              <div className="rounded-[24px] border border-white/10 bg-bg/60 p-5 text-sm text-textMuted">
                No provider keys stored yet.
              </div>
            )}
          </div>

          <div className="mt-8 rounded-[24px] border border-accent/20 bg-accentSoft p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent">Security Note</p>
            <p className="mt-3 text-sm leading-6 text-textMain">
              Raw keys are never returned to the frontend after save. The backend encrypts them and uses them only during execution.
            </p>
          </div>

          <div className="mt-4 rounded-[24px] border border-white/10 bg-bg/60 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-textMuted">Target Site Login</p>
            <p className="mt-3 text-sm leading-6 text-textMuted">
              Website username/password for scraping are set per run on the Landing or Run page. They are not managed as global provider keys here.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AiIntegrationsPage;
