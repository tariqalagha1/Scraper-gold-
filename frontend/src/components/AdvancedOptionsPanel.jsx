import React, { useState } from 'react';

const focusClass = 'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950';

const AdvancedOptionsPanel = ({ workspace, setWorkspace, mode = 'structured' }) => {
  const [open, setOpen] = useState(false);

  const update = (key, value) => {
    setWorkspace((previous) => ({ ...previous, [key]: value }));
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className={`flex w-full items-center justify-between px-4 py-3 text-left ${focusClass}`}
        aria-expanded={open}
        aria-controls="advanced-options-content"
      >
        <span className="text-sm font-medium text-slate-200">Advanced Options</span>
        <span className="text-xs text-slate-400">{open ? 'Hide' : 'Show'}</span>
      </button>

      {open && (
        <div id="advanced-options-content" className="space-y-4 border-t border-white/10 px-4 py-4">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1 text-sm">
              <label htmlFor="advanced-target-url" className="text-slate-400">
                URL override
              </label>
              <input
                id="advanced-target-url"
                value={workspace.targetUrl || ''}
                onChange={(event) => update('targetUrl', event.target.value)}
                placeholder="https://example.com"
                className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 placeholder:text-slate-500 ${focusClass}`}
              />
            </div>

            <div className="space-y-1 text-sm">
              <label htmlFor="advanced-location" className="text-slate-400">
                Location (structured mode)
              </label>
              <input
                id="advanced-location"
                value={workspace.location || ''}
                onChange={(event) => update('location', event.target.value)}
                placeholder="Saudi Arabia"
                className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 placeholder:text-slate-500 ${focusClass}`}
              />
            </div>

            <div className="space-y-1 text-sm">
              <label htmlFor="advanced-limit" className="text-slate-400">
                Max records
              </label>
              <input
                id="advanced-limit"
                type="number"
                min="1"
                max="500"
                value={workspace.limit || 50}
                onChange={(event) => update('limit', event.target.value)}
                className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 ${focusClass}`}
              />
            </div>

            <div className="space-y-1 text-sm">
              <label htmlFor="advanced-max-pages" className="text-slate-400">
                Max pages
              </label>
              <input
                id="advanced-max-pages"
                type="number"
                min="1"
                max="1000"
                value={workspace.maxPages || 10}
                onChange={(event) => update('maxPages', event.target.value)}
                className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 ${focusClass}`}
              />
            </div>
          </div>

          <div className="flex items-center gap-2 text-sm text-slate-300">
            <input
              id="advanced-follow-pagination"
              type="checkbox"
              checked={Boolean(workspace.followPagination)}
              onChange={(event) => update('followPagination', event.target.checked)}
              className={`h-4 w-4 rounded border-white/20 bg-slate-900 ${focusClass}`}
            />
            <label htmlFor="advanced-follow-pagination">Follow pagination automatically</label>
          </div>

          {mode === 'website' && (
            <div className="grid gap-3 md:grid-cols-4">
              <div className="space-y-1 text-sm">
                <label htmlFor="advanced-page-expansion-mode" className="text-slate-400">
                  Page expansion mode
                </label>
                <select
                  id="advanced-page-expansion-mode"
                  value={workspace.pageExpansionMode || 'same_domain'}
                  onChange={(event) => update('pageExpansionMode', event.target.value)}
                  className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 ${focusClass}`}
                >
                  <option value="main_only">Main page only</option>
                  <option value="same_domain">Same-site linked pages</option>
                  <option value="connected_external">Connected external links</option>
                </select>
              </div>

              <div className="space-y-1 text-sm">
                <label htmlFor="advanced-linked-page-limit" className="text-slate-400">
                  Linked pages limit
                </label>
                <input
                  id="advanced-linked-page-limit"
                  type="number"
                  min="1"
                  max="1000"
                  value={workspace.linkedPageLimit || 20}
                  onChange={(event) => update('linkedPageLimit', event.target.value)}
                  className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 ${focusClass}`}
                />
              </div>

              <div className="space-y-1 text-sm">
                <label htmlFor="advanced-linked-page-workers" className="text-slate-400">
                  Linked page workers
                </label>
                <input
                  id="advanced-linked-page-workers"
                  type="number"
                  min="1"
                  max="16"
                  value={workspace.linkedPageWorkers || 4}
                  onChange={(event) => update('linkedPageWorkers', event.target.value)}
                  className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 ${focusClass}`}
                />
              </div>

              <div className="space-y-1 text-sm md:col-span-1">
                <label htmlFor="advanced-linked-keywords" className="text-slate-400">
                  Linked page keywords
                </label>
                <input
                  id="advanced-linked-keywords"
                  value={workspace.linkedPageKeywords || ''}
                  onChange={(event) => update('linkedPageKeywords', event.target.value)}
                  placeholder="price, product, user, details"
                  className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 placeholder:text-slate-500 ${focusClass}`}
                />
              </div>
            </div>
          )}

          {mode === 'structured' && (
            <div className="block space-y-1 text-sm">
              <label htmlFor="advanced-fields" className="text-slate-400">
                Structured field overrides (comma-separated)
              </label>
              <input
                id="advanced-fields"
                value={workspace.fieldsText || ''}
                onChange={(event) => update('fieldsText', event.target.value)}
                placeholder="name, email, phone, website"
                className={`w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 placeholder:text-slate-500 ${focusClass}`}
              />
            </div>
          )}

          <div className="rounded-xl border border-white/10 bg-slate-900 p-3">
            <div className="flex items-center gap-2 text-sm text-slate-300">
              <input
                id="advanced-requires-login"
                type="checkbox"
                checked={Boolean(workspace.requiresLogin)}
                onChange={(event) => update('requiresLogin', event.target.checked)}
                className={`h-4 w-4 rounded border-white/20 bg-slate-900 ${focusClass}`}
              />
              <label htmlFor="advanced-requires-login">Website requires login</label>
            </div>

            {workspace.requiresLogin && (
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div className="space-y-1 text-sm md:col-span-2">
                  <label htmlFor="advanced-login-url" className="text-slate-400">
                    Login URL
                  </label>
                  <input
                    id="advanced-login-url"
                    value={workspace.loginUrl || ''}
                    onChange={(event) => update('loginUrl', event.target.value)}
                    placeholder="https://example.com/login"
                    className={`w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-slate-100 placeholder:text-slate-500 ${focusClass}`}
                  />
                </div>

                <div className="space-y-1 text-sm">
                  <label htmlFor="advanced-login-username" className="text-slate-400">
                    Username / email
                  </label>
                  <input
                    id="advanced-login-username"
                    value={workspace.loginUsername || ''}
                    onChange={(event) => update('loginUsername', event.target.value)}
                    className={`w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-slate-100 ${focusClass}`}
                  />
                </div>

                <div className="space-y-1 text-sm">
                  <label htmlFor="advanced-login-password" className="text-slate-400">
                    Password
                  </label>
                  <input
                    id="advanced-login-password"
                    type="password"
                    value={workspace.loginPassword || ''}
                    onChange={(event) => update('loginPassword', event.target.value)}
                    className={`w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-slate-100 ${focusClass}`}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AdvancedOptionsPanel;
