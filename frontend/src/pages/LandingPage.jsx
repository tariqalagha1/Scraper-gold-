import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { storeLandingExtractionIntent } from '../utils/extractionIntent';

const consoleDefinitions = [
  {
    key: 'detecting',
    number: '01',
    icon: 'radar',
    title: 'Inspecting target',
    body: 'Checking the page type, access needs, and the best scraping strategy.',
  },
  {
    key: 'crawling',
    number: '02',
    icon: 'travel_explore',
    title: 'Collecting pages',
    body: 'Following links and pagination to gather the content you asked for.',
  },
  {
    key: 'parsing',
    number: '03',
    icon: 'schema',
    title: 'Extracting fields',
    body: 'Pulling titles, prices, availability, documents, or other target fields.',
  },
  {
    key: 'structuring',
    number: '04',
    icon: 'data_object',
    title: 'Preparing output',
    body: 'Turning raw page content into rows, JSON, and export-ready results.',
  },
];

const capabilityCards = [
  {
    id: 'structured',
    title: 'Structured Data Extraction',
    body: 'Capture product catalogs, listings, tables, and directories into clean result rows you can review and export.',
    className: 'md:col-span-8',
  },
  {
    id: 'protected',
    title: 'Protected Pages',
    body: 'Pass login details for websites that require authentication before the scraper can continue.',
    className: 'md:col-span-4',
  },
  {
    id: 'documents',
    title: 'Documents and Media',
    body: 'Switch from general scraping to collecting PDFs, images, and other downloadable assets.',
    className: 'md:col-span-4',
  },
  {
    id: 'exports',
    title: 'Results and Reuse',
    body: 'Keep recent requests, inspect the latest run, and move structured output into downstream workflows.',
    className: 'md:col-span-8',
  },
];

const useCases = [
  {
    id: 'catalog',
    title: 'Extract catalog data',
    eyebrow: 'Structured Records',
    body: 'Collect titles, prices, ratings, and stock status from product or listing pages.',
    prompt: 'Extract structured product data',
  },
  {
    id: 'documents',
    title: 'Download documents',
    eyebrow: 'PDF Collection',
    body: 'Gather linked PDFs, reports, manuals, or attachments from a public website.',
    prompt: 'Download all PDF files linked from this website',
  },
  {
    id: 'images',
    title: 'Collect images',
    eyebrow: 'Media Capture',
    body: 'Save product shots, gallery images, or listing thumbnails from category pages.',
    prompt: 'Collect all product images and their source pages',
  },
  {
    id: 'protected',
    title: 'Scrape a protected site',
    eyebrow: 'Authenticated Access',
    body: 'Pass login details, then extract tables, account data, or member-only content.',
    prompt: 'Scrape the protected dashboard after login and extract table rows',
  },
];

const engagementGraphSteps = [
  { title: 'Inspect', caption: 'Target page checked', tone: 'done' },
  { title: 'Collect', caption: 'Pages and links queued', tone: 'active' },
  { title: 'Extract', caption: 'Fields mapped to records', tone: 'done' },
  { title: 'Validate', caption: 'Missing fields reviewed', tone: 'pending' },
  { title: 'Deliver', caption: 'Results ready to export', tone: 'pending' },
];

const advancedFeatures = [
  {
    title: 'Recent Request Memory',
    status: 'Available',
    body: 'Frequently used scraping prompts can be reopened from the dashboard instead of being typed again.',
  },
  {
    title: 'Protected Site Handoff',
    status: 'Available',
    body: 'Landing-page login details move directly into the authenticated job flow when a website requires sign-in.',
  },
  {
    title: 'Export-Ready Output',
    status: 'Available',
    body: 'Structured results stay readable in the dashboard and can be handed off to JSON or export flows.',
  },
];

const successJson = `{
  "status": "success",
  "source": "https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
  "summary": {
    "scrape_type": "structured",
    "pages_scanned": 12,
    "records": 24
  },
  "records": [
    {
      "title": "It's Only the Himalayas",
      "category": "Travel",
      "price": "GBP 45.17",
      "availability": "In stock"
    },
    {
      "title": "Full Moon over Noah's Ark",
      "category": "Travel",
      "price": "GBP 49.43",
      "availability": "In stock"
    }
  ]
}`;

const errorJson = `{
  "status": "error",
  "source": "https://example.com/private",
  "error": {
    "code": "AUTH_REQUIRED",
    "message": "The target page requires valid login details before scraping can continue."
  }
}`;

const actionRows = [
  { action: 'open_target(url)', state: 'done' },
  { action: 'check_access_rules()', state: 'done' },
  { action: 'extract_records()', state: 'active' },
  { action: 'validate_fields()', state: 'pending' },
  { action: 'prepare_export()', state: 'pending' },
];

const LandingPage = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const [url, setUrl] = useState('https://books.toscrape.com/catalogue/category/books/travel_2/index.html');
  const [prompt, setPrompt] = useState('Extract structured product data');
  const [requiresLogin, setRequiresLogin] = useState(false);
  const [loginUrl, setLoginUrl] = useState('');
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [selectedUseCase, setSelectedUseCase] = useState('pricing');
  const [activeConsoleStep, setActiveConsoleStep] = useState('detecting');
  const [completedConsoleSteps, setCompletedConsoleSteps] = useState([]);
  const [systemFeedback, setSystemFeedback] = useState('Ready for a scraping request.');
  const [outputView, setOutputView] = useState('dashboard');
  const [resultState, setResultState] = useState('loading');
  const [copyVisible, setCopyVisible] = useState(false);
  const [latency, setLatency] = useState('1.8s');
  const [activeAgents, setActiveAgents] = useState('0 / 25');
  const [nodeActivity, setNodeActivity] = useState('Waiting');

  const rawJson = useMemo(() => (resultState === 'error' ? errorJson : successJson), [resultState]);

  useEffect(() => {
    const feedbackMap = {
      detecting: 'Checking the target URL and deciding how the scraper should approach the page...',
      crawling: 'Following links, pagination, and visible content that match the request...',
      parsing: 'Extracting fields from the collected pages and shaping them into records...',
      structuring: 'Preparing dashboard rows, raw JSON, and export-ready output...',
    };

    setSystemFeedback(feedbackMap[activeConsoleStep] || 'Ready for a scraping request.');
  }, [activeConsoleStep]);

  const handleRun = () => {
    storeLandingExtractionIntent({
      url,
      prompt: prompt.trim() || 'Extract structured product data',
      max_pages: 25,
      follow_pagination: true,
      requiresLogin,
      login_url: requiresLogin ? loginUrl.trim() || '' : null,
      login_username: requiresLogin ? loginUsername.trim() || '' : null,
      login_password: requiresLogin ? (isAuthenticated ? loginPassword : '') : null,
    });
    navigate(isAuthenticated ? '/dashboard' : '/login');
  };

  const runPreview = () => {
    setResultState('loading');
    setOutputView('dashboard');
    setCompletedConsoleSteps([]);
    setActiveConsoleStep('detecting');
    setLatency('1.8s');
    setActiveAgents('0 / 25');
    setNodeActivity('Checking target');

    window.clearTimeout(window.__aardvarkPreviewStep1);
    window.clearTimeout(window.__aardvarkPreviewStep2);
    window.clearTimeout(window.__aardvarkPreviewStep3);
    window.clearTimeout(window.__aardvarkPreviewStep4);

    window.__aardvarkPreviewStep1 = window.setTimeout(() => {
      setCompletedConsoleSteps(['detecting']);
      setActiveConsoleStep('crawling');
      setLatency('2.4s');
      setActiveAgents('6 / 25');
      setNodeActivity('Following links');
    }, 500);

    window.__aardvarkPreviewStep2 = window.setTimeout(() => {
      setCompletedConsoleSteps(['detecting', 'crawling']);
      setActiveConsoleStep('parsing');
      setLatency('3.1s');
      setActiveAgents('18 / 25');
      setNodeActivity('Extracting fields');
    }, 1100);

    window.__aardvarkPreviewStep3 = window.setTimeout(() => {
      setCompletedConsoleSteps(['detecting', 'crawling', 'parsing']);
      setActiveConsoleStep('structuring');
      setNodeActivity('Building results');
      setResultState('success');
    }, 1700);

    window.__aardvarkPreviewStep4 = window.setTimeout(() => {
      setCompletedConsoleSteps(['detecting', 'crawling', 'parsing', 'structuring']);
      setNodeActivity('Ready for review');
      setLatency('3.6s');
      setActiveAgents('25 / 25');
    }, 2300);
  };

  const handleUseCaseSelect = (useCase) => {
    setSelectedUseCase(useCase.id);
    setPrompt(useCase.prompt);
    setResultState('loading');
    runPreview();
  };

  const handleCopyJson = async () => {
    try {
      await navigator.clipboard.writeText(rawJson);
      setCopyVisible(true);
      window.setTimeout(() => setCopyVisible(false), 1600);
    } catch (_error) {
      setCopyVisible(true);
      window.setTimeout(() => setCopyVisible(false), 1600);
    }
  };

  const handleExportJson = () => {
    const blob = new Blob([rawJson], { type: 'application/json' });
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = 'smart-scraper-preview-output.json';
    link.click();
    URL.revokeObjectURL(href);
  };

  return (
    <div className="overflow-x-hidden">
      <section className="relative px-6 pb-12 pt-8 lg:px-8">
        <div className="aardvark-grid absolute inset-0 opacity-40" />
        <div className="absolute left-1/2 top-[12%] h-[42rem] w-[42rem] -translate-x-1/2 rounded-full bg-accent/10 blur-[140px]" />

        <div className="mx-auto max-w-[1440px]">
          <div className="grid items-center gap-12 lg:grid-cols-12">
            <div className="lg:col-span-7">
              <div className="space-y-4">
                <div className="inline-flex items-center gap-3 rounded-full border border-accent/15 bg-accentSoft px-4 py-2">
                  <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
                  <span className="font-label text-[10px] uppercase tracking-[0.28em] text-primaryFixedDim">
                    SCRAPER WORKSPACE // LIVE PREVIEW
                  </span>
                </div>
                <h1 className="max-w-4xl font-headline text-5xl font-bold tracking-[-0.06em] text-onBackground sm:text-6xl lg:text-8xl">
                  Smart <span className="text-primary">Scraper</span>
                </h1>
                <p className="max-w-2xl text-base leading-8 text-onSurfaceVariant sm:text-lg">
                  Turn a website URL and a plain-English request into usable scraping jobs, structured results, and export-ready data.
                </p>
              </div>

              <div className="glass-panel mt-10 rounded-[1.75rem] border border-outlineVariant/15 p-5 shadow-panel">
                <div className="flex flex-col gap-4">
                  <input
                    value={url}
                    onChange={(event) => setUrl(event.target.value)}
                    className="rounded-2xl border border-outlineVariant/20 bg-surfaceContainerLowest/80 px-5 py-4 text-sm text-onBackground outline-none placeholder:text-onSurfaceVariant/60 focus:border-primary/35"
                    placeholder="https://books.toscrape.com/catalogue/category/books/travel_2/index.html"
                  />

                  <textarea
                    value={prompt}
                    onChange={(event) => setPrompt(event.target.value)}
                    rows={3}
                    className="resize-none rounded-2xl border border-outlineVariant/20 bg-surfaceContainerLowest/80 px-5 py-4 text-sm text-onBackground outline-none placeholder:text-onSurfaceVariant/60 focus:border-primary/35"
                    placeholder="Describe what to scrape: extract products, collect PDFs, download images, or capture table rows..."
                  />

                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={handleRun}
                      className="gel-shadow tonal-gradient rounded-xl px-6 py-4 font-headline text-sm font-bold uppercase tracking-[0.22em] text-onPrimary transition hover:scale-[1.02]"
                    >
                      Run Extraction
                    </button>
                    <button
                      type="button"
                      onClick={runPreview}
                      className="rounded-xl border border-outlineVariant/20 bg-surfaceContainerHigh px-5 py-4 font-label text-sm uppercase tracking-[0.22em] text-onSurface transition hover:border-primary/35 hover:text-primary"
                    >
                      View Demo Flow
                    </button>
                    <div className="rounded-full border border-primary/15 bg-accentSoft px-4 py-2 font-label text-[10px] uppercase tracking-[0.22em] text-primary">
                      Scraper Ready
                    </div>
                  </div>

                  <div className="rounded-2xl border border-outlineVariant/15 bg-surfaceContainerLow p-4">
                    <label className="flex cursor-pointer items-center gap-3 text-sm text-onBackground">
                      <input
                        type="checkbox"
                        checked={requiresLogin}
                        onChange={(event) => setRequiresLogin(event.target.checked)}
                        className="h-4 w-4 rounded border border-outlineVariant/20 bg-surfaceContainerLowest accent-primary"
                      />
                      Protected page access (optional)
                    </label>
                    <p className="mt-2 text-xs uppercase tracking-[0.16em] text-onSurfaceVariant">
                      Use this when the target website requires login before scraping.
                    </p>

                    {requiresLogin ? (
                      <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        <input
                          value={loginUrl}
                          onChange={(event) => setLoginUrl(event.target.value)}
                          className="rounded-xl border border-outlineVariant/20 bg-surfaceContainerLowest px-4 py-3 text-sm text-onBackground outline-none placeholder:text-onSurfaceVariant/60 focus:border-primary/35 sm:col-span-2"
                          placeholder="Login URL (optional)"
                        />
                        <input
                          value={loginUsername}
                          onChange={(event) => setLoginUsername(event.target.value)}
                          className="rounded-xl border border-outlineVariant/20 bg-surfaceContainerLowest px-4 py-3 text-sm text-onBackground outline-none placeholder:text-onSurfaceVariant/60 focus:border-primary/35"
                          placeholder="Username or email"
                        />
                        <input
                          type="password"
                          value={loginPassword}
                          onChange={(event) => setLoginPassword(event.target.value)}
                          className="rounded-xl border border-outlineVariant/20 bg-surfaceContainerLowest px-4 py-3 text-sm text-onBackground outline-none placeholder:text-onSurfaceVariant/60 focus:border-primary/35"
                          placeholder="Password"
                        />
                      </div>
                    ) : null}
                  </div>

                  <div className="rounded-2xl border border-outlineVariant/15 bg-surfaceContainerLow p-4">
                    <div className="grid gap-3 md:grid-cols-4">
                      {consoleDefinitions.map((step) => {
                        const stateClass = completedConsoleSteps.includes(step.key)
                          ? 'done'
                          : activeConsoleStep === step.key
                            ? 'active'
                            : '';

                        return (
                          <div
                            key={step.key}
                            className={`console-step rounded-xl bg-surfaceContainerLow px-4 py-3 ${stateClass}`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">
                                {step.number}
                              </span>
                              <span
                                className={`material-symbols-outlined text-sm ${
                                  activeConsoleStep === step.key ? 'console-pulse text-primary' : 'text-onSurfaceVariant'
                                }`}
                              >
                                {step.icon}
                              </span>
                            </div>
                            <div className="mt-3 font-headline text-sm font-semibold text-onSurface">{step.title}</div>
                            <div className="mt-1 text-xs text-onSurfaceVariant">{step.body}</div>
                          </div>
                        );
                      })}
                    </div>

                    <div className="mt-3 rounded-xl bg-surfaceContainerLowest px-4 py-3 text-sm text-onSurfaceVariant">
                      {systemFeedback}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="relative lg:col-span-5">
              <div className="aardvark-stage relative flex min-h-[680px] items-center justify-center">
                <div className="absolute inset-0 rounded-full bg-primary/10 blur-[120px]" />
                <div className="hero-ring hero-ring-outer" />
                <div className="hero-ring hero-ring-middle" />
                <div className="hero-ring hero-ring-inner" />
                <div className="hero-orb animate-hero-core">
                  <div className="hero-orb__scan" />
                  <div className="hero-orb__grid" />
                  <div className="hero-orb__nodes">
                    <span className="hero-node hero-node-1" />
                    <span className="hero-node hero-node-2" />
                    <span className="hero-node hero-node-3" />
                    <span className="hero-node hero-node-4" />
                    <span className="hero-node hero-node-5" />
                  </div>
                </div>

                <div className="floating-hud floating-hud-left glass-panel absolute left-2 top-10 animate-float-1 rounded-2xl border border-outlineVariant/15 px-4 py-3">
                  <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">Run Time</div>
                  <div className="mt-2 font-headline text-xl font-bold text-primary">{latency}</div>
                </div>

                <div className="floating-hud floating-hud-right glass-panel absolute right-0 top-28 animate-float-2 rounded-2xl border border-outlineVariant/15 px-4 py-3">
                  <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">Current Stage</div>
                  <div className="mt-2 font-headline text-lg font-bold text-primary">{nodeActivity}</div>
                </div>

                <div className="floating-hud floating-hud-bottom glass-panel absolute bottom-8 left-8 animate-float-3 rounded-2xl border border-outlineVariant/15 px-4 py-3">
                  <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">Pages</div>
                  <div className="mt-2 font-headline text-xl font-bold text-primary">{activeAgents}</div>
                </div>

                <div className="floating-hud floating-hud-mini glass-panel absolute bottom-20 right-8 rounded-2xl border border-outlineVariant/15 px-4 py-3">
                  <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">Field Match</div>
                  <div className="mt-2 font-headline text-lg font-bold text-primary">97.8%</div>
                </div>

                <div className="relative z-10 max-w-sm text-center">
                  <div className="inline-flex items-center gap-3 rounded-full border border-primary/20 bg-accentSoft px-4 py-2">
                    <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                    <span className="font-label text-[10px] uppercase tracking-[0.24em] text-primaryFixedDim">
                      Live Run Preview
                    </span>
                  </div>
                  <p className="mt-6 font-headline text-3xl font-bold text-onBackground">Scraping pipeline snapshot</p>
                  <p className="mt-3 text-sm leading-7 text-onSurfaceVariant">
                    Watch the request move from target inspection to collected records, then into a dashboard-ready result.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 pb-14 lg:px-8">
          <div className="mx-auto grid max-w-[1440px] grid-cols-2 gap-4 md:grid-cols-6">
            <div className="depth-tile space-y-2 rounded-xl border-l-2 border-primaryFixedDim/30 bg-surfaceContainerLow p-6">
              <div className="font-label text-[10px] uppercase tracking-widest text-onSurfaceVariant/60">Run_Time</div>
              <div className="font-headline text-2xl font-medium text-primary">{latency}</div>
            </div>
          <div className="depth-tile space-y-2 rounded-xl border-l-2 border-primaryFixedDim/30 bg-surfaceContainerLow p-6">
            <div className="font-label text-[10px] uppercase tracking-widest text-onSurfaceVariant/60">Pages_Scanned</div>
            <div className="font-headline text-2xl font-medium text-primary">{activeAgents}</div>
          </div>
          <div className="depth-tile space-y-2 rounded-xl border-l-2 border-primaryFixedDim/30 bg-surfaceContainerLow p-6">
            <div className="font-label text-[10px] uppercase tracking-widest text-onSurfaceVariant/60">Scrape_Type</div>
            <div className="font-headline text-2xl font-medium text-primary">Structured</div>
          </div>
          <div className="depth-tile space-y-2 rounded-xl border-l-2 border-primaryFixedDim/30 bg-surfaceContainerLow p-6">
            <div className="font-label text-[10px] uppercase tracking-widest text-onSurfaceVariant/60">Protected_Access</div>
            <div className="font-headline text-2xl font-medium text-primary">{requiresLogin ? 'Enabled' : 'Off'}</div>
          </div>
          <div className="depth-tile space-y-2 rounded-xl border-l-2 border-primaryFixedDim/30 bg-surfaceContainerLow p-6">
            <div className="font-label text-[10px] uppercase tracking-widest text-onSurfaceVariant/60">Current_Stage</div>
            <div className="font-headline text-2xl font-medium text-primary">{nodeActivity}</div>
          </div>
          <div className="depth-tile space-y-2 rounded-xl border-l-2 border-primaryFixedDim/30 bg-surfaceContainerLow p-6">
            <div className="font-label text-[10px] uppercase tracking-widest text-onSurfaceVariant/60">Result_State</div>
            <div className="font-headline text-2xl font-medium text-primary">
              {resultState === 'loading' ? 'Standby' : resultState === 'success' ? 'Success' : 'Error'}
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 pb-24 lg:px-8">
        <div className="mx-auto max-w-[1440px] rounded-[1.75rem] border border-outlineVariant/10 p-6 glass-panel">
          <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="font-label text-[10px] uppercase tracking-[0.32em] text-primary">Quick Start Templates</div>
              <h2 className="mt-2 font-headline text-3xl font-bold tracking-tight text-onBackground">Common Scraping Requests</h2>
              <p className="mt-2 max-w-2xl text-sm text-onSurfaceVariant">
                Click a template to load a realistic scraping prompt into the request box and preview the run flow.
              </p>
            </div>
            <div className="rounded-full bg-surfaceContainerHigh px-3 py-1 font-label text-[10px] uppercase tracking-[0.24em] text-primaryFixedDim">
              Templates Ready
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-4">
            {useCases.map((useCase) => (
              <button
                key={useCase.id}
                type="button"
                onClick={() => handleUseCaseSelect(useCase)}
                className={`use-case-card depth-tile rounded-2xl border border-outlineVariant/15 bg-surfaceContainerHigh p-5 text-left ${
                  selectedUseCase === useCase.id ? 'is-selected' : ''
                }`}
              >
                <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">{useCase.eyebrow}</div>
                <div className="mt-3 font-headline text-xl font-semibold text-onSurface">{useCase.title}</div>
                <p className="mt-2 text-sm text-onSurfaceVariant">{useCase.body}</p>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="relative bg-surfaceContainerLow/30 px-6 py-24 lg:px-8" id="modules">
        <div className="mx-auto max-w-[1440px]">
          <div className="mb-16 space-y-4">
            <h2 className="font-label text-xs uppercase tracking-[0.4em] text-primary">Core Workflow</h2>
            <h3 className="font-headline text-4xl font-bold tracking-tight text-onBackground md:text-5xl">Built for real scraping tasks</h3>
          </div>

          <div className="grid gap-6 md:grid-cols-12">
            {capabilityCards.map((card) => (
              <div
                key={card.id}
                className={`group capability-surface relative overflow-hidden rounded-3xl border border-outlineVariant/10 bg-surfaceContainerHigh p-10 transition-colors hover:border-primary/30 ${card.className}`}
              >
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,211,160,0.10),transparent_22%)] opacity-80" />
                <div className="relative z-10 max-w-md">
                  <h4 className="mb-4 font-headline text-3xl font-bold text-onBackground">{card.title}</h4>
                  <p className="leading-relaxed text-onSurfaceVariant">{card.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-24 lg:px-8">
        <div className="mx-auto max-w-[1440px] rounded-[2rem] border border-outlineVariant/10 bg-surfaceContainer/70 p-6 shadow-panel lg:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-label text-[11px] uppercase tracking-[0.24em] text-primary">Run Timeline</p>
              <h2 className="mt-2 font-headline text-3xl font-bold text-onBackground">See the scraping run unfold, not just the final answer</h2>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-onSurfaceVariant">
                This view keeps the run understandable while it works: inspect the page, collect content, extract records, validate fields, and deliver results.
              </p>
            </div>
            <div className="rounded-full border border-primary/15 bg-accentSoft px-4 py-2 font-label text-[10px] uppercase tracking-[0.22em] text-primary">
              Live preview
            </div>
          </div>

          <div className="mt-8 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-[1.5rem] border border-outlineVariant/10 bg-surfaceContainerLowest/70 p-4">
              <div className="grid gap-3 md:grid-cols-[repeat(5,minmax(0,1fr))]">
                {engagementGraphSteps.map((step, index) => (
                  <div key={step.title} className="relative">
                    <div
                      className={`rounded-2xl border px-4 py-4 ${
                        step.tone === 'done'
                          ? 'border-tertiary/30 bg-tertiary/10 text-tertiary'
                          : step.tone === 'active'
                            ? 'border-primary/30 bg-accentSoft text-primary'
                            : 'border-outlineVariant/15 bg-surfaceContainerLow text-onSurfaceVariant'
                      }`}
                    >
                      <p className="font-label text-[10px] uppercase tracking-[0.2em] opacity-70">Step {index + 1}</p>
                      <p className="mt-2 font-headline text-base font-bold">{step.title}</p>
                      <p className="mt-2 text-sm opacity-80">{step.caption}</p>
                    </div>
                    {index < engagementGraphSteps.length - 1 ? <div className="mx-auto hidden h-8 w-px bg-outlineVariant/20 md:block" /> : null}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[1.5rem] border border-outlineVariant/10 bg-surfaceContainerLowest p-4 shadow-panel">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.22em] text-onSurfaceVariant">Example Scraper Actions</p>
                  <p className="mt-2 text-sm text-onSurfaceVariant">This log-style preview shows the kind of steps a real run performs before results appear.</p>
                </div>
                <div className="rounded-full border border-outlineVariant/15 bg-surfaceContainerHigh px-3 py-1 font-label text-[10px] uppercase tracking-[0.16em] text-onSurface">
                  62% progress
                </div>
              </div>
              <div className="mt-4 space-y-2 font-mono text-sm">
                {actionRows.map((item) => (
                  <div
                    key={item.action}
                    className={`flex items-center justify-between rounded-xl border px-3 py-2 ${
                      item.state === 'done'
                        ? 'border-tertiary/20 bg-tertiary/10 text-tertiary'
                        : item.state === 'active'
                          ? 'border-primary/30 bg-accentSoft text-primary'
                          : 'border-outlineVariant/15 bg-white/[0.03] text-onSurfaceVariant'
                    }`}
                  >
                    <span>{item.action}</span>
                    <span className="font-label text-[10px] uppercase tracking-[0.2em]">
                      {item.state === 'done' ? 'done' : item.state === 'active' ? 'live' : 'queued'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 py-24 lg:px-8" id="output-panel">
        <div className="mx-auto max-w-[1440px] rounded-[1.75rem] border border-outlineVariant/10 p-6 glass-panel">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="font-label text-[10px] uppercase tracking-[0.32em] text-primary">Output Panel</div>
              <h2 className="mt-2 font-headline text-4xl font-bold tracking-tight text-onBackground">Live Extraction Output</h2>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-onSurfaceVariant">
                Switch between a readable dashboard preview and the raw JSON payload so the output feels useful, not decorative.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleCopyJson}
                className="rounded-xl border border-outlineVariant/20 bg-surfaceContainerHigh px-4 py-3 font-label text-xs uppercase tracking-[0.18em] text-onSurface transition-colors hover:bg-surfaceBright"
              >
                Copy JSON
              </button>
              <button
                type="button"
                onClick={handleExportJson}
                className="rounded-xl border border-outlineVariant/20 bg-surfaceContainerHigh px-4 py-3 font-label text-xs uppercase tracking-[0.18em] text-onSurface transition-colors hover:bg-surfaceBright"
              >
                Export Result
              </button>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setOutputView('dashboard')}
              className={`output-tab rounded-full px-4 py-2 font-label text-xs uppercase tracking-[0.18em] ${
                outputView === 'dashboard'
                  ? 'active bg-surfaceContainerHigh text-primary'
                  : 'bg-surfaceContainerLow text-onSurfaceVariant'
              }`}
            >
              Dashboard View
            </button>
            <button
              type="button"
              onClick={() => setOutputView('json')}
              className={`output-tab rounded-full px-4 py-2 font-label text-xs uppercase tracking-[0.18em] ${
                outputView === 'json'
                  ? 'active bg-surfaceContainerHigh text-primary'
                  : 'bg-surfaceContainerLow text-onSurfaceVariant'
              }`}
            >
              Raw JSON View
            </button>
          </div>

          <div className={`copy-feedback mt-3 text-sm text-primary ${copyVisible ? 'show' : ''}`}>JSON copied to clipboard.</div>

          <div className={`result-state mt-6 ${resultState === 'loading' ? 'is-visible' : ''}`}>
            <div className="rounded-2xl border border-outlineVariant/10 bg-surfaceContainerLow p-5">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined animate-spin text-primary">progress_activity</span>
                <div>
                  <div className="font-headline text-xl font-semibold text-onSurface">Preparing extraction preview</div>
                  <p className="mt-1 text-sm text-onSurfaceVariant">The interface is stepping through target inspection, collection, and record-building.</p>
                </div>
              </div>
            </div>
          </div>

          <div className={`result-state mt-6 ${resultState === 'success' ? 'is-visible' : ''}`}>
            <div className="rounded-2xl border border-outlineVariant/10 bg-surfaceContainerLow p-5">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-tertiary">verified</span>
                <div>
                  <div className="font-headline text-xl font-semibold text-onSurface">Extraction preview ready</div>
                  <p className="mt-1 text-sm text-onSurfaceVariant">Structured results are ready for dashboard review, JSON inspection, and export.</p>
                </div>
              </div>
            </div>
          </div>

          <div className={`result-state mt-6 ${resultState === 'error' ? 'is-visible' : ''}`}>
            <div className="rounded-2xl border border-errorContainer/30 bg-errorContainer/10 p-5">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-error">error</span>
                <div>
                  <div className="font-headline text-xl font-semibold text-onErrorContainer">Target needs attention</div>
                  <p className="mt-1 text-sm text-onErrorContainer/80">The scraper could not continue with the current page setup. Check the URL, login details, or request scope and try again.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className={`${outputView === 'dashboard' ? 'block' : 'hidden'} space-y-6`}>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-outlineVariant/10 bg-surfaceContainerHigh p-5">
                  <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">Records Captured</div>
                  <div className="mt-3 font-headline text-3xl font-bold text-primary">24</div>
                  <div className="mt-2 text-sm text-onSurfaceVariant">Rows collected from the sample target and prepared for review.</div>
                </div>
                <div className="rounded-2xl border border-outlineVariant/10 bg-surfaceContainerHigh p-5">
                  <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">Field Coverage</div>
                  <div className="mt-3 font-headline text-3xl font-bold text-primary">97.8%</div>
                  <div className="mt-2 text-sm text-onSurfaceVariant">Most requested fields were found across the collected records.</div>
                </div>
                <div className="rounded-2xl border border-outlineVariant/10 bg-surfaceContainerHigh p-5">
                  <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">Pages Scanned</div>
                  <div className="mt-3 font-headline text-3xl font-bold text-primary">12</div>
                  <div className="mt-2 text-sm text-onSurfaceVariant">The preview run walked through multiple pages before finalizing the sample output.</div>
                </div>
              </div>

              <div className="table-shell rounded-2xl border border-outlineVariant/10 p-5">
                <div className="mb-4 flex items-end justify-between gap-4">
                  <div>
                    <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">Visual Dashboard</div>
                    <h3 className="mt-2 font-headline text-2xl font-bold text-onBackground">Structured Results Table</h3>
                  </div>
                  <div className="rounded-full bg-surfaceContainerHigh px-3 py-1 font-label text-[10px] uppercase tracking-[0.22em] text-tertiary">Preview rows</div>
                </div>

                <div className="overflow-hidden rounded-xl">
                  <table className="w-full text-left">
                    <thead className="bg-surfaceContainerHighest/60">
                      <tr className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">
                        <th className="px-4 py-3">Title</th>
                        <th className="px-4 py-3">Category</th>
                        <th className="px-4 py-3">Price</th>
                        <th className="px-4 py-3">Availability</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-outlineVariant/10 text-sm text-onSurface">
                      <tr>
                        <td className="px-4 py-4">It&apos;s Only the Himalayas</td>
                        <td className="px-4 py-4">Travel</td>
                        <td className="px-4 py-4 text-primary">GBP 45.17</td>
                        <td className="px-4 py-4">In stock</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-4">Full Moon over Noah&apos;s Ark</td>
                        <td className="px-4 py-4">Travel</td>
                        <td className="px-4 py-4 text-primary">GBP 49.43</td>
                        <td className="px-4 py-4">In stock</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-4">See America</td>
                        <td className="px-4 py-4">Travel</td>
                        <td className="px-4 py-4 text-primary">GBP 48.87</td>
                        <td className="px-4 py-4">In stock</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className={`${outputView === 'json' ? 'block' : 'hidden'} space-y-6`}>
              <div className="rounded-2xl border border-outlineVariant/10 bg-surfaceContainerHigh p-5">
                <div className="mb-4 flex items-end justify-between gap-4">
                  <div>
                    <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">Raw JSON</div>
                    <h3 className="mt-2 font-headline text-2xl font-bold text-onBackground">Scraper Response</h3>
                  </div>
                  <div className="rounded-full bg-surfaceContainerLow px-3 py-1 font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">api/v1 preview</div>
                </div>
                <pre className="code-block">{rawJson}</pre>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 py-24 lg:px-8" id="api-preview">
        <div className="mx-auto max-w-[1440px] rounded-[1.75rem] border border-outlineVariant/10 p-6 glass-panel">
          <div className="mb-8">
            <div className="font-label text-[10px] uppercase tracking-[0.32em] text-primary">API Preview</div>
            <h2 className="mt-2 font-headline text-4xl font-bold tracking-tight text-onBackground">Frontend Request Flow</h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-onSurfaceVariant">
              Show the same kind of request flow the app uses: create a job, then start a run and review the returned results.
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-2xl border border-outlineVariant/10 bg-surfaceContainerHigh p-5">
              <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">Example Request</div>
              <pre className="code-block mt-4">{`POST /api/v1/jobs
{
  "url": "https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
  "prompt": "Extract structured product data",
  "scrape_type": "structured",
  "max_pages": 10,
  "follow_pagination": true
}`}</pre>
            </div>

            <div className="rounded-2xl border border-outlineVariant/10 bg-surfaceContainerHigh p-5">
              <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">Example Response</div>
              <pre className="code-block mt-4">{`201 Created
{
  "job": {
    "id": 18,
    "url": "https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
    "scrape_type": "structured"
  },
  "next": "POST /api/v1/jobs/18/runs"
}`}</pre>
            </div>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {advancedFeatures.map((feature) => (
              <div key={feature.title} className="advanced-feature-card rounded-2xl border border-outlineVariant/10 bg-surfaceContainerHigh p-5">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-label text-[10px] uppercase tracking-[0.22em] text-primaryFixedDim">Advanced Feature</div>
                    <div className="mt-2 font-headline text-xl font-semibold text-onSurface">{feature.title}</div>
                  </div>
                  <span className="feature-status-pill">{feature.status}</span>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-onSurfaceVariant">{feature.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="relative px-6 py-32 text-center lg:px-8">
        <div className="mx-auto max-w-4xl space-y-10">
          <h2 className="font-headline text-4xl font-bold tracking-tight text-onBackground md:text-6xl">
            Ready to run your next <span className="italic text-primary">scrape</span>?
          </h2>
          <div className="flex flex-col items-center justify-center gap-6 md:flex-row">
            <button
              type="button"
              onClick={handleRun}
              className="gel-shadow tonal-gradient w-full rounded-xl px-10 py-5 font-headline text-lg font-bold uppercase text-onPrimary md:w-auto"
            >
              Start Extraction
            </button>
            <button
              type="button"
              onClick={() => setOutputView('json')}
              className="w-full rounded-xl border border-outlineVariant/30 bg-surfaceContainerHigh px-10 py-5 font-headline text-lg font-bold uppercase text-onSurface transition-colors hover:bg-surfaceBright md:w-auto"
            >
              Open JSON Preview
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
