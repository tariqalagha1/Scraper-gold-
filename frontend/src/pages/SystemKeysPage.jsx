import React, { useEffect, useMemo, useState } from 'react';
import api, { extractApiErrorMessage } from '../services/api';
import { PageHeader, PrimaryButton, Section } from '../components/ui';

const SYSTEM_KEYS = [
  { name: 'SECRET_KEY', label: 'JWT Secret Key', note: 'Changing this invalidates existing sessions/tokens.' },
  { name: 'API_KEY', label: 'Global API Key', note: 'Used for protected API route access via X-API-Key.' },
  { name: 'SCRAPER_API_KEY', label: 'Scraper Service API Key', note: 'Used to call external scraper service.' },
  { name: 'OPENAI_API_KEY', label: 'OpenAI API Key', note: 'Fallback key for orchestration/analysis/embeddings.' },
];

const focusClass = 'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950';

const SystemKeysPage = () => {
  const [items, setItems] = useState([]);
  const [values, setValues] = useState({});
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState('');
  const [deletingKey, setDeletingKey] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  const byName = useMemo(() => {
    const mapping = {};
    for (const item of items) {
      mapping[item.name] = item;
    }
    return mapping;
  }, [items]);

  const loadSystemKeys = async () => {
    try {
      setLoading(true);
      const secrets = await api.getSystemKeys();
      setItems(secrets || []);
      setError('');
    } catch (loadError) {
      setError(extractApiErrorMessage(loadError, 'Could not load system keys.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSystemKeys();
  }, []);

  const handleSave = async (name) => {
    const rawValue = String(values[name] || '').trim();
    if (!rawValue) {
      setError(`Enter a value for ${name} before saving.`);
      return;
    }

    try {
      setSavingKey(name);
      await api.saveSystemKey(name, { value: rawValue });
      setValues((previous) => ({ ...previous, [name]: '' }));
      setNotice(`${name} saved securely.`);
      setError('');
      await loadSystemKeys();
    } catch (saveError) {
      setError(extractApiErrorMessage(saveError, `Could not save ${name}.`));
    } finally {
      setSavingKey('');
    }
  };

  const handleDelete = async (name) => {
    if (deletingKey) return;

    const confirmed = typeof window === 'undefined' || window.confirm(`Delete ${name} override?`);
    if (!confirmed) return;

    try {
      setDeletingKey(name);
      await api.deleteSystemKey(name);
      setNotice(`${name} database override removed.`);
      setError('');
      await loadSystemKeys();
    } catch (deleteError) {
      setError(extractApiErrorMessage(deleteError, `Could not delete ${name}.`));
    } finally {
      setDeletingKey('');
    }
  };

  return (
    <section className="space-y-4">
      <PageHeader
        title="System Keys"
        description="Manage global encrypted keys used by backend services. Values are never returned in raw form."
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

      <Section title="Operational Notes">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>Keys are encrypted at rest and only shown as masks after saving.</li>
          <li>API and worker processes may need restart in some deployment topologies to pick up changes everywhere.</li>
          <li>Changing `SECRET_KEY` invalidates existing auth tokens immediately.</li>
        </ul>
      </Section>

      <Section title="Manage Keys" description="One input per required key for reliable SaaS operation.">
        {loading ? (
          <p className="text-sm text-slate-400">Loading system keys...</p>
        ) : (
          <div className="space-y-4">
            {SYSTEM_KEYS.map((keyDef) => {
              const item = byName[keyDef.name];
              const configured = Boolean(item?.configured);
              const source = item?.source || 'unset';
              const masked = item?.key_mask || 'Not configured';

              return (
                <div key={keyDef.name} className="rounded-xl border border-white/10 bg-slate-900 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-slate-100">{keyDef.label}</p>
                      <p className="text-xs text-slate-400">{keyDef.name}</p>
                      <p className="mt-1 text-xs text-slate-500">{keyDef.note}</p>
                    </div>
                    <span className="rounded-full border border-white/10 bg-slate-800 px-2 py-1 text-xs text-slate-300">
                      {configured ? `Configured (${source})` : 'Not configured'}
                    </span>
                  </div>

                  <p className="mt-2 text-xs text-slate-400">Current mask: {masked}</p>

                  <div className="mt-3 grid gap-2 md:grid-cols-[1fr_auto_auto]">
                    <input
                      type="password"
                      placeholder={`Set ${keyDef.name}`}
                      value={values[keyDef.name] || ''}
                      onChange={(event) =>
                        setValues((previous) => ({ ...previous, [keyDef.name]: event.target.value }))
                      }
                      className={`w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 ${focusClass}`}
                    />
                    <PrimaryButton
                      type="button"
                      onClick={() => handleSave(keyDef.name)}
                      disabled={savingKey === keyDef.name}
                    >
                      {savingKey === keyDef.name ? 'Saving...' : 'Save'}
                    </PrimaryButton>
                    <button
                      type="button"
                      onClick={() => handleDelete(keyDef.name)}
                      disabled={!configured || deletingKey === keyDef.name}
                      className={`rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-2 text-sm text-red-200 transition hover:border-red-300 disabled:cursor-not-allowed disabled:opacity-60 ${focusClass}`}
                    >
                      {deletingKey === keyDef.name ? 'Removing...' : 'Remove'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Section>
    </section>
  );
};

export default SystemKeysPage;

