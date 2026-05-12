import React, { useEffect, useMemo, useState } from 'react';
import api, { extractApiErrorMessage } from '../services/api';
import { PageHeader, PrimaryButton, Section } from '../components/ui';

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'serper', label: 'Serper' },
  { value: 'gemini', label: 'Gemini' },
];

const focusClass = 'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950';

const IntegrationsPage = () => {
  const [provider, setProvider] = useState('openai');
  const [apiKey, setApiKey] = useState('');
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const currentCredential = useMemo(
    () => credentials.find((item) => item.provider === provider) || null,
    [credentials, provider]
  );

  const loadCredentials = async () => {
    try {
      setLoading(true);
      const items = await api.getCredentials();
      setCredentials(items || []);
      setError('');
    } catch (loadError) {
      setError(extractApiErrorMessage(loadError, 'Could not load provider credentials.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCredentials();
  }, []);

  const handleSave = async () => {
    const normalizedKey = String(apiKey || '').trim();
    if (!normalizedKey) {
      setError('Enter an API key before saving.');
      return;
    }

    try {
      setSaving(true);
      const saved = await api.saveCredential({ provider, api_key: normalizedKey });
      setCredentials((previous) => {
        const next = previous.filter((item) => item.provider !== saved.provider);
        return [...next, saved].sort((left, right) => left.provider.localeCompare(right.provider));
      });
      setApiKey('');
      setError('');
      setNotice(`${provider} key saved securely.`);
    } catch (saveError) {
      setError(extractApiErrorMessage(saveError, 'Could not save provider key.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (targetProvider) => {
    if (!targetProvider || removing) return;

    try {
      setRemoving(targetProvider);
      await api.deleteCredential(targetProvider);
      setCredentials((previous) => previous.filter((item) => item.provider !== targetProvider));
      setNotice(`${targetProvider} key removed.`);
      setError('');
    } catch (removeError) {
      setError(extractApiErrorMessage(removeError, 'Could not remove provider key.'));
    } finally {
      setRemoving('');
    }
  };

  return (
    <section className="space-y-4">
      <PageHeader
        title="Integrations"
        description="Manage AI provider credentials and verify connection status."
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
        <Section title="Manage provider key" description="Add or rotate one provider key at a time.">
          <div className="space-y-3">
            <div className="space-y-1 text-sm">
              <label htmlFor="integration-provider" className="text-slate-400">
                Provider
              </label>
              <select
                id="integration-provider"
                value={provider}
                onChange={(event) => setProvider(event.target.value)}
                className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 ${focusClass}`}
              >
                {PROVIDERS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1 text-sm">
              <label htmlFor="integration-api-key" className="text-slate-400">
                API key
              </label>
              <input
                id="integration-api-key"
                type="password"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder="Paste provider key"
                className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 placeholder:text-slate-500 ${focusClass}`}
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <PrimaryButton type="button" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : currentCredential ? 'Update key' : 'Save key'}
              </PrimaryButton>

              {currentCredential && (
                <button
                  type="button"
                  onClick={() => handleDelete(provider)}
                  disabled={removing === provider}
                  className={`w-full rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-2 text-sm text-red-200 transition hover:border-red-300 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto ${focusClass}`}
                >
                  {removing === provider ? 'Removing...' : 'Remove key'}
                </button>
              )}
            </div>
          </div>
        </Section>

        <Section title="Provider status" description="Credentials are masked after save and managed server-side.">
          {loading ? (
            <p className="text-sm text-slate-400">Loading providers...</p>
          ) : (
            <ul className="space-y-2">
              {PROVIDERS.map((item) => {
                const credential = credentials.find((entry) => entry.provider === item.value);
                const connected = Boolean(credential);

                return (
                  <li key={item.value} className="rounded-xl border border-white/10 bg-slate-900 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-medium text-slate-100">{item.label}</p>
                        {credential ? (
                          <p className="text-xs text-slate-400">{credential.key_mask}</p>
                        ) : (
                          <p className="text-xs text-slate-500">No key saved</p>
                        )}
                      </div>

                      <span
                        className={`rounded-full border px-2 py-1 text-xs ${
                          connected
                            ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-200'
                            : 'border-white/10 bg-slate-800 text-slate-400'
                        }`}
                      >
                        {connected ? 'Connected' : 'Not connected'}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Security note">
        <p className="text-sm text-slate-300">
          Provider credentials are not returned in raw form after saving. Target-site login details are configured per run in
          Home Advanced Options.
        </p>
      </Section>
    </section>
  );
};

export default IntegrationsPage;
