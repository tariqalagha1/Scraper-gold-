import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './DashboardPage.css';
import api, { extractApiErrorMessage } from '../services/api';
import { detectScrapeType } from '../assistant/orchestrator';

const settingTags = ['Active', 'AI Infra', 'Priority Review', 'Q2 Launch'];
const visibilityOptions = ['Internal Only', 'Client Shared', 'Executive Review'];
const categoryOptions = ['All Workstreams', 'Platform', 'Intelligence', 'Design', 'Operations'];
const defaultPreferences = {
  visibility: 'Internal Only',
  category_filter: 'All Workstreams',
  notifications: {
    budget_warnings: true,
    overdue_tasks: true,
    milestone_alerts: true,
    executive_digest: false,
  },
  plan_tags: [...settingTags],
};

const isValidHttpUrl = (value) => {
  try {
    const parsed = new URL(String(value || '').trim());
    return ['http:', 'https:'].includes(parsed.protocol);
  } catch {
    return false;
  }
};

const normalizePreferences = (raw) => {
  const payload = raw && typeof raw === 'object' ? raw : {};
  const notifications = payload.notifications && typeof payload.notifications === 'object'
    ? payload.notifications
    : {};

  return {
    visibility: visibilityOptions.includes(payload.visibility)
      ? payload.visibility
      : defaultPreferences.visibility,
    category_filter: categoryOptions.includes(payload.category_filter)
      ? payload.category_filter
      : defaultPreferences.category_filter,
    notifications: {
      budget_warnings: Boolean(notifications.budget_warnings ?? defaultPreferences.notifications.budget_warnings),
      overdue_tasks: Boolean(notifications.overdue_tasks ?? defaultPreferences.notifications.overdue_tasks),
      milestone_alerts: Boolean(notifications.milestone_alerts ?? defaultPreferences.notifications.milestone_alerts),
      executive_digest: Boolean(notifications.executive_digest ?? defaultPreferences.notifications.executive_digest),
    },
    plan_tags: Array.isArray(payload.plan_tags)
      ? payload.plan_tags.filter((tag) => typeof tag === 'string' && settingTags.includes(tag))
      : [...defaultPreferences.plan_tags],
  };
};

const notificationToggles = [
  { key: 'budget_warnings', label: 'Budget Warnings' },
  { key: 'overdue_tasks', label: 'Overdue Tasks' },
  { key: 'milestone_alerts', label: 'Milestone Alerts' },
  { key: 'executive_digest', label: 'Executive Digest' },
];

const milestones = [
  { name: 'Project Created: Command Center', status: 'Known', tone: 'complete' },
  { name: 'Screen Confirmed: Aardvark Intelligence 3D Landing Page', status: 'Known', tone: 'complete' },
  { name: 'Milestones and delivery dates', status: 'Missing', tone: 'planning' },
];

const kpiCards = [
  {
    label: 'AI Integrations',
    title: 'Provider Keys & Models',
    description: 'Manage OpenAI, Anthropic, Gemini, and search provider keys used by your agents.',
    route: '/ai-integrations',
    actionLabel: 'Open Integrations',
  },
  {
    label: 'API Keys',
    title: 'External Automation Access',
    description: 'Create and rotate Smart Scraper API keys used by scripts and partner systems.',
    route: '/api-keys',
    actionLabel: 'Open API Keys',
  },
  {
    label: 'Workspace',
    title: 'Live Run Control',
    description: 'Monitor pipeline execution, logs, outputs, and reruns from one operational view.',
    route: '/workspace',
    actionLabel: 'Open Workspace',
  },
  {
    label: 'Storage & Privacy',
    title: 'Cleanup & Retention',
    description: 'Control history cleanup, temporary files, and local privacy-safe maintenance.',
    route: '/settings',
    actionLabel: 'Open Settings',
  },
];

const timelineEntries = [
  {
    state: 'Known',
    title: 'Project Identified',
    description: 'Command Center with project ID 1444918229901845874 was provided in the Stitch instructions.',
  },
  {
    state: 'Known',
    title: 'Screen Identified',
    description: 'Aardvark Intelligence 3D Landing Page is the explicit screen currently mapped in design files.',
  },
  {
    state: 'Missing',
    title: 'Milestone Schedule',
    description: 'No phase dates, target milestones, or delivery windows were included in the available plan data.',
  },
  {
    state: 'Missing',
    title: 'Launch Target',
    description: 'No launch date, release gate, or reporting deadline is present in the source plan.',
  },
];

const DashboardPage = () => {
  const navigate = useNavigate();
  const [preferences, setPreferences] = useState(defaultPreferences);
  const [hasLoadedPreferences, setHasLoadedPreferences] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [savedAt, setSavedAt] = useState('');
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [requestText, setRequestText] = useState('');
  const [requiresLogin, setRequiresLogin] = useState(false);
  const [loginCredentials, setLoginCredentials] = useState({
    loginUrl: '',
    username: '',
    password: '',
  });
  const [workflowError, setWorkflowError] = useState('');
  const [workflowMessage, setWorkflowMessage] = useState('');
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [workflowSubmitting, setWorkflowSubmitting] = useState(false);
  const [assistantMessage, setAssistantMessage] = useState('');
  const [refinedPrompt, setRefinedPrompt] = useState('');
  const [recommendedType, setRecommendedType] = useState('');
  const [pageExpansionMode, setPageExpansionMode] = useState('same_domain');
  const [linkedPageLimit, setLinkedPageLimit] = useState('20');
  const [linkedPageWorkers, setLinkedPageWorkers] = useState('4');
  const [linkedPageKeywords, setLinkedPageKeywords] = useState('price, product, user, details');
  const [clarifyingQuestions, setClarifyingQuestions] = useState([]);
  const [followUpAnswers, setFollowUpAnswers] = useState({});
  const [capabilities, setCapabilities] = useState(null);
  const [executionMode, setExecutionMode] = useState('single_source');
  const [executionLimit, setExecutionLimit] = useState('50');
  const [executionSources, setExecutionSources] = useState({
    internal: false,
    google_maps: false,
    web: true,
  });
  const [executionControls, setExecutionControls] = useState({
    fallback: true,
    early_stop: true,
    retry: true,
  });
  const [optionalAgents, setOptionalAgents] = useState({
    analysis_agent: false,
    vector_agent: false,
    export_agent: false,
  });

  useEffect(() => {
    let isMounted = true;

    const loadPreferences = async () => {
      try {
        const response = await api.getDashboardPreferences();
        if (!isMounted) return;
        setPreferences(normalizePreferences(response?.preferences));
        setSavedAt(String(response?.updated_at || ''));
        setSaveError('');
      } catch {
        if (!isMounted) return;
        setSaveError('Could not load saved dashboard settings. Using defaults for now.');
      } finally {
        if (isMounted) setHasLoadedPreferences(true);
      }
    };

    loadPreferences();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    const loadCapabilities = async () => {
      try {
        const response = await api.getSystemCapabilities();
        const contract = response?.execution_contract || null;
        if (!isMounted || !contract) return;

        setCapabilities(contract);
        setExecutionMode('single_source');
        setExecutionSources({
          internal: false,
          google_maps: false,
          web: true,
        });
        setExecutionLimit(String(contract.limit?.default || 50));
        setExecutionControls({
          fallback: Boolean(contract.controls?.fallback ?? true),
          early_stop: Boolean(contract.controls?.early_stop ?? true),
          retry: Boolean(contract.controls?.retry ?? true),
        });
        setOptionalAgents({
          analysis_agent: false,
          vector_agent: false,
          export_agent: false,
        });
      } catch {
        // Keep local defaults if capabilities are temporarily unavailable.
      }
    };

    loadCapabilities();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!hasLoadedPreferences || !isDirty) return undefined;

    const timer = window.setTimeout(async () => {
      setIsSaving(true);
      try {
        const response = await api.updateDashboardPreferences(preferences);
        setPreferences(normalizePreferences(response?.preferences));
        setSavedAt(String(response?.updated_at || new Date().toISOString()));
        setSaveError('');
        setIsDirty(false);
      } catch {
        setSaveError('Could not save dashboard settings. Your latest change is local only.');
      } finally {
        setIsSaving(false);
      }
    }, 450);

    return () => window.clearTimeout(timer);
  }, [preferences, hasLoadedPreferences, isDirty]);

  const saveStatusLabel = useMemo(() => {
    if (!hasLoadedPreferences) return 'Loading saved settings...';
    if (isSaving) return 'Saving settings...';
    if (saveError) return saveError;
    if (savedAt) return `Saved ${new Date(savedAt).toLocaleTimeString()}`;
    return 'Saved preferences not found yet.';
  }, [hasLoadedPreferences, isSaving, saveError, savedAt]);
  const controlsDisabled = !hasLoadedPreferences;
  const effectivePrompt = refinedPrompt.trim() || requestText.trim();
  const availableSources = Array.isArray(capabilities?.sources) && capabilities.sources.length > 0
    ? capabilities.sources
    : ['internal', 'google_maps', 'web'];
  const availableModes = Array.isArray(capabilities?.execution_modes) && capabilities.execution_modes.length > 0
    ? capabilities.execution_modes
    : ['single_source', 'multi_source'];
  const availableOptionalAgents = Array.isArray(capabilities?.optional_agents) && capabilities.optional_agents.length > 0
    ? capabilities.optional_agents
    : ['analysis_agent', 'vector_agent', 'export_agent'];

  const buildExecutionContract = () => {
    const selectedSources = availableSources.filter((source) => executionSources[source]);
    if (selectedSources.length === 0) {
      throw new Error('Select at least one source in Execution Builder.');
    }
    const minLimit = Number(capabilities?.limit?.min || 1);
    const maxLimit = Number(capabilities?.limit?.max || 100);
    const parsedLimit = Number(executionLimit);
    const normalizedLimit = Number.isFinite(parsedLimit) ? Math.round(parsedLimit) : Number(capabilities?.limit?.default || 50);
    const boundedLimit = Math.max(minLimit, Math.min(maxLimit, normalizedLimit));
    const mode = executionMode === 'single_source' ? 'single_source' : 'multi_source';
    const effectiveSources = mode === 'single_source' ? [selectedSources[0]] : selectedSources;
    const selectedOptionalAgents = availableOptionalAgents.filter((agent) => optionalAgents[agent]);

    return {
      agents: [
        'policy_service',
        'strategic_execution_service',
        'multi_source_service',
        'quality_layer',
        'event_emitter',
        'control_service',
      ],
      optional_agents: selectedOptionalAgents,
      execution_mode: mode,
      sources: effectiveSources,
      limit: boundedLimit,
      controls: {
        fallback: Boolean(executionControls.fallback),
        early_stop: Boolean(executionControls.early_stop),
        retry: Boolean(executionControls.retry),
      },
    };
  };

  const getWorkflowErrorMessage = (error, fallback) => {
    return extractApiErrorMessage(error, fallback);
  };

  const handleVisibilityChange = (event) => {
    if (controlsDisabled) return;
    setPreferences((previous) => ({ ...previous, visibility: event.target.value }));
    setIsDirty(true);
  };

  const handleCategoryChange = (event) => {
    if (controlsDisabled) return;
    setPreferences((previous) => ({ ...previous, category_filter: event.target.value }));
    setIsDirty(true);
  };

  const handleNotificationToggle = (key) => (event) => {
    if (controlsDisabled) return;
    setPreferences((previous) => ({
      ...previous,
      notifications: {
        ...previous.notifications,
        [key]: event.target.checked,
      },
    }));
    setIsDirty(true);
  };

  const handleTagToggle = (tag) => {
    if (controlsDisabled) return;
    setPreferences((previous) => {
      const hasTag = previous.plan_tags.includes(tag);
      return {
        ...previous,
        plan_tags: hasTag
          ? previous.plan_tags.filter((item) => item !== tag)
          : [...previous.plan_tags, tag],
      };
    });
    setIsDirty(true);
  };

  const validateCoreWorkflow = () => {
    if (!websiteUrl.trim()) {
      return 'Add the website URL to start a run.';
    }
    if (!isValidHttpUrl(websiteUrl)) {
      return 'Use a valid URL that starts with http:// or https://.';
    }
    if (!effectivePrompt.trim()) {
      return 'Describe what you want the scraper to collect.';
    }

    if (requiresLogin) {
      const { loginUrl, username, password } = loginCredentials;
      if (!String(loginUrl || '').trim() || !String(username || '').trim() || !String(password || '').trim()) {
        return 'Protected websites need login URL, username, and password.';
      }
      if (!isValidHttpUrl(loginUrl)) {
        return 'Use a valid login URL for protected-site access.';
      }
    }
    return '';
  };

  const handleRefineRequest = async () => {
    const intentText = requestText.trim();
    if (!intentText) {
      setWorkflowError('Write your request first, then click Refine with AI.');
      return;
    }

    setAssistantLoading(true);
    setWorkflowError('');
    setWorkflowMessage('');

    const conversation = clarifyingQuestions
      .map((question) => {
        const answer = String(followUpAnswers[question] || '').trim();
        if (!answer) return null;
        return { role: 'user', content: `Question: ${question}\nAnswer: ${answer}` };
      })
      .filter(Boolean);

    try {
      const response = await api.refineScrapeRequest({
        url: websiteUrl.trim() || null,
        draft_prompt: effectivePrompt || null,
        user_message: intentText,
        conversation,
      });

      setAssistantMessage(String(response?.assistant_message || '').trim());
      setRefinedPrompt(String(response?.refined_prompt || '').trim());
      setRecommendedType(String(response?.recommended_scrape_type || '').trim());
      setClarifyingQuestions(Array.isArray(response?.clarifying_questions) ? response.clarifying_questions : []);
      setWorkflowMessage('AI guidance is ready. Review it, then run.');
    } catch (error) {
      setWorkflowError(getWorkflowErrorMessage(error, 'AI refinement is unavailable right now.'));
    } finally {
      setAssistantLoading(false);
    }
  };

  const handleStartRun = async () => {
    const validationError = validateCoreWorkflow();
    if (validationError) {
      setWorkflowError(validationError);
      return;
    }

    setWorkflowSubmitting(true);
    setWorkflowError('');
    setWorkflowMessage('Creating job and starting run...');

    try {
      const executionContract = buildExecutionContract();
      const payload = {
        url: websiteUrl.trim(),
        prompt: effectivePrompt.trim(),
        scrape_type: detectScrapeType(effectivePrompt) || 'general',
        max_pages: 10,
        follow_pagination: true,
        config: {
          page_expansion_mode: String(pageExpansionMode || 'same_domain'),
          linked_page_limit: Math.max(1, Math.min(1000, Number(linkedPageLimit) || 20)),
          linked_page_workers: Math.max(1, Math.min(16, Number(linkedPageWorkers) || 4)),
          linked_page_keywords: String(linkedPageKeywords || '')
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
        },
        login_url: requiresLogin ? loginCredentials.loginUrl.trim() : null,
        login_username: requiresLogin ? loginCredentials.username.trim() : null,
        login_password: requiresLogin ? loginCredentials.password.trim() : null,
      };

      const createdJob = await api.createJob(payload);
      await api.startJobRun(createdJob.id, { executionContract, job: createdJob });
      setWorkflowMessage('Run started. Opening workspace...');
      navigate(`/workspace/${createdJob.id}`);
    } catch (error) {
      setWorkflowError(getWorkflowErrorMessage(error, 'Could not create the job. Please try again.'));
      setWorkflowMessage('');
    } finally {
      setWorkflowSubmitting(false);
    }
  };

  return (
    <section className="command-center-dashboard">
    <aside className="settings-sidebar surface-low">
      <div className="sidebar-header">
        <span className="eyebrow">Project Settings</span>
        <h2>Sovereign Controls</h2>
        <p>Filters, visibility, notifications, and reporting behavior for the active plan.</p>
      </div>

      <section className="settings-group surface-panel">
        <label className="field-label" htmlFor="visibility-filter">Visibility</label>
        <select
          id="visibility-filter"
          className="sovereign-select"
          value={preferences.visibility}
          onChange={handleVisibilityChange}
          disabled={controlsDisabled}
        >
          {visibilityOptions.map((option) => (
            <option key={option}>{option}</option>
          ))}
        </select>
      </section>

      <section className="settings-group surface-panel">
        <label className="field-label" htmlFor="category-filter">Category Filter</label>
        <select
          id="category-filter"
          className="sovereign-select"
          value={preferences.category_filter}
          onChange={handleCategoryChange}
          disabled={controlsDisabled}
        >
          {categoryOptions.map((option) => (
            <option key={option}>{option}</option>
          ))}
        </select>
      </section>

      <section className="settings-group surface-panel">
        <span className="field-label">Notifications</span>
        {notificationToggles.map((toggle) => (
          <label className="toggle-row" key={toggle.label}>
            <span>{toggle.label}</span>
            <input
              type="checkbox"
              checked={Boolean(preferences.notifications[toggle.key])}
              onChange={handleNotificationToggle(toggle.key)}
              disabled={controlsDisabled}
            />
          </label>
        ))}
      </section>

      <section className="settings-group surface-panel">
        <span className="field-label">Plan Tags</span>
        <div className="chip-stack">
          {settingTags.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => handleTagToggle(tag)}
              className={`data-chip ${preferences.plan_tags.includes(tag) ? 'chip-warm' : 'chip-neutral'}`}
              disabled={controlsDisabled}
            >
              {tag}
            </button>
          ))}
        </div>
        <p className={`settings-status ${saveError ? 'error' : ''}`}>{saveStatusLabel}</p>
      </section>
    </aside>

    <main className="dashboard-main">
      <header className="dashboard-header glass-panel">
        <div className="header-copy">
          <span className="eyebrow">Project 1444918229901845874</span>
          <h1>Command Center</h1>
          <div className="header-meta">
            <span className="status-pill status-planning">Plan Data Pending</span>
            <span className="meta-item">Screen: Aardvark Intelligence 3D Landing Page</span>
            <span className="meta-item">Screen ID: 0d6b9dfab32f46eeb8de97f5550d1eb0</span>
            <span className="meta-item">Owner: Not provided in source files</span>
          </div>
        </div>

        <div className="header-actions">
          <Link to="/settings" className="button button-secondary">Edit Plan</Link>
          <Link to="/workspace" className="button button-secondary">Add Task</Link>
          <Link to="/exports" className="button button-primary">Export Report</Link>
        </div>
      </header>

      <section className="core-workflow glass-panel">
        <div className="section-title">
          <span className="eyebrow">Main Workflow</span>
          <h2>Website + Credentials + AI</h2>
        </div>
        <p className="workflow-intro">
          Start everything from here: define the website, add protected-page credentials, refine with AI, and launch the run.
        </p>

        <div className="workflow-grid">
          <label className="workflow-field">
            <span className="field-label">Website URL</span>
            <input
              type="url"
              value={websiteUrl}
              onChange={(event) => setWebsiteUrl(event.target.value)}
              placeholder="https://example.com/catalog"
              className="workflow-input"
            />
          </label>

          <label className="workflow-field workflow-field-wide">
            <span className="field-label">AI Request</span>
            <textarea
              value={requestText}
              onChange={(event) => setRequestText(event.target.value)}
              placeholder="Collect product name, price, and stock from each listing page."
              rows={4}
              className="workflow-input workflow-textarea"
            />
          </label>
        </div>

        <label className="toggle-row workflow-toggle">
          <span>Website requires login</span>
          <input
            type="checkbox"
            checked={requiresLogin}
            onChange={(event) => setRequiresLogin(event.target.checked)}
          />
        </label>

        {requiresLogin && (
          <div className="workflow-grid credentials-grid">
            <label className="workflow-field">
              <span className="field-label">Login URL</span>
              <input
                type="url"
                value={loginCredentials.loginUrl}
                onChange={(event) =>
                  setLoginCredentials((previous) => ({ ...previous, loginUrl: event.target.value }))
                }
                placeholder="https://example.com/login"
                className="workflow-input"
              />
            </label>
            <label className="workflow-field">
              <span className="field-label">Username / Email</span>
              <input
                type="text"
                value={loginCredentials.username}
                onChange={(event) =>
                  setLoginCredentials((previous) => ({ ...previous, username: event.target.value }))
                }
                placeholder="user@example.com"
                className="workflow-input"
              />
            </label>
            <label className="workflow-field">
              <span className="field-label">Password</span>
              <input
                type="password"
                value={loginCredentials.password}
                onChange={(event) =>
                  setLoginCredentials((previous) => ({ ...previous, password: event.target.value }))
                }
                placeholder="Enter password"
                className="workflow-input"
              />
            </label>
          </div>
        )}

        <div className="workflow-grid">
          <label className="workflow-field">
            <span className="field-label">Page Expansion Mode</span>
            <select
              className="workflow-input"
              value={pageExpansionMode}
              onChange={(event) => setPageExpansionMode(event.target.value)}
            >
              <option value="main_only">Main page only</option>
              <option value="same_domain">Same-site linked pages</option>
              <option value="connected_external">Connected external links</option>
            </select>
          </label>

          <label className="workflow-field">
            <span className="field-label">Linked Pages Limit</span>
            <input
              type="number"
              min="1"
              max="1000"
              value={linkedPageLimit}
              onChange={(event) => setLinkedPageLimit(event.target.value)}
              className="workflow-input"
            />
          </label>

          <label className="workflow-field">
            <span className="field-label">Linked Page Workers</span>
            <input
              type="number"
              min="1"
              max="16"
              value={linkedPageWorkers}
              onChange={(event) => setLinkedPageWorkers(event.target.value)}
              className="workflow-input"
            />
          </label>

          <label className="workflow-field workflow-field-wide">
            <span className="field-label">Linked Page Keywords</span>
            <input
              type="text"
              value={linkedPageKeywords}
              onChange={(event) => setLinkedPageKeywords(event.target.value)}
              placeholder="price, product, user, details"
              className="workflow-input"
            />
          </label>
        </div>

        <section className="workflow-ai-output surface-panel">
          <span className="eyebrow">Execution Builder</span>
          <p className="workflow-meta">Define exactly what the runtime executes for this run.</p>

          <div className="workflow-grid">
            <label className="workflow-field">
              <span className="field-label">Execution Mode</span>
              <select
                className="workflow-input"
                value={executionMode}
                onChange={(event) => setExecutionMode(event.target.value)}
              >
                {availableModes.map((mode) => (
                  <option key={mode} value={mode}>{mode}</option>
                ))}
              </select>
            </label>
            <label className="workflow-field">
              <span className="field-label">Result Limit</span>
              <input
                type="number"
                min={Number(capabilities?.limit?.min || 1)}
                max={Number(capabilities?.limit?.max || 100)}
                value={executionLimit}
                onChange={(event) => setExecutionLimit(event.target.value)}
                className="workflow-input"
              />
            </label>
          </div>

          <div className="workflow-grid">
            <div className="workflow-field workflow-field-wide">
              <span className="field-label">Sources</span>
              <div className="chip-stack">
                {availableSources.map((source) => (
                  <label key={source} className="toggle-row">
                    <span>{source}</span>
                    <input
                      type="checkbox"
                      checked={Boolean(executionSources[source])}
                      onChange={(event) =>
                        setExecutionSources((previous) => ({
                          ...previous,
                          [source]: event.target.checked,
                        }))
                      }
                    />
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="workflow-grid">
            <div className="workflow-field workflow-field-wide">
              <span className="field-label">Controls</span>
              <div className="chip-stack">
                {['fallback', 'early_stop', 'retry'].map((control) => (
                  <label key={control} className="toggle-row">
                    <span>{control}</span>
                    <input
                      type="checkbox"
                      checked={Boolean(executionControls[control])}
                      onChange={(event) =>
                        setExecutionControls((previous) => ({
                          ...previous,
                          [control]: event.target.checked,
                        }))
                      }
                    />
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="workflow-grid">
            <div className="workflow-field workflow-field-wide">
              <span className="field-label">Optional Agents</span>
              <div className="chip-stack">
                {availableOptionalAgents.map((agent) => (
                  <label key={agent} className="toggle-row">
                    <span>{agent}</span>
                    <input
                      type="checkbox"
                      checked={Boolean(optionalAgents[agent])}
                      onChange={(event) =>
                        setOptionalAgents((previous) => ({
                          ...previous,
                          [agent]: event.target.checked,
                        }))
                      }
                    />
                  </label>
                ))}
              </div>
            </div>
          </div>
        </section>

        <div className="workflow-actions">
          <button
            type="button"
            className="button button-secondary"
            onClick={handleRefineRequest}
            disabled={assistantLoading || workflowSubmitting}
          >
            {assistantLoading ? 'Refining...' : 'Refine with AI'}
          </button>
          <button
            type="button"
            className="button button-primary"
            onClick={handleStartRun}
            disabled={workflowSubmitting || assistantLoading}
          >
            {workflowSubmitting ? 'Starting...' : 'Create Job & Start Run'}
          </button>
          <Link to="/ai-integrations" className="button button-secondary">
            AI Provider Keys
          </Link>
        </div>

        {workflowError && <p className="workflow-alert workflow-alert-error">{workflowError}</p>}
        {workflowMessage && <p className="workflow-alert workflow-alert-info">{workflowMessage}</p>}

        {(refinedPrompt || assistantMessage || recommendedType || clarifyingQuestions.length > 0) && (
          <section className="workflow-ai-output surface-panel">
            <span className="eyebrow">AI Assistant</span>
            {recommendedType && <p className="workflow-meta">Suggested scrape type: {recommendedType}</p>}
            {assistantMessage && <p className="workflow-ai-message">{assistantMessage}</p>}
            {refinedPrompt && (
              <div>
                <span className="field-label">Refined Request</span>
                <p className="workflow-refined-prompt">{refinedPrompt}</p>
              </div>
            )}
            {clarifyingQuestions.length > 0 && (
              <div className="workflow-questions">
                {clarifyingQuestions.map((question) => (
                  <label key={question} className="workflow-field">
                    <span className="field-label">{question}</span>
                    <input
                      type="text"
                      value={followUpAnswers[question] || ''}
                      onChange={(event) =>
                        setFollowUpAnswers((previous) => ({ ...previous, [question]: event.target.value }))
                      }
                      className="workflow-input"
                    />
                  </label>
                ))}
              </div>
            )}
          </section>
        )}
      </section>

      <section className="hero-grid">
        <article className="hero-priority glass-panel urgent-panel">
          <span className="eyebrow">Urgent Signal</span>
          <h2>Top-left attention zone</h2>
          <p>Surface overdue tasks, budget warnings, and blockers first so high-risk data is visible before secondary metrics.</p>

          <div className="source-note surface-panel">
            <strong>Source coverage</strong>
            <p>
              The design package includes the project title, project ID, screen name, and style direction,
              but no real budget, owner roster, milestone dates, or task counts.
            </p>
          </div>

          <div className="warning-cluster">
            <div className="warning-card surface-panel warning-high">
              <span className="warning-label">Overdue Tasks</span>
              <strong>Not provided</strong>
              <p>No overdue-task count was included in the source plan data.</p>
            </div>

            <div className="warning-card surface-panel warning-medium">
              <span className="warning-label">Budget Risk</span>
              <strong>Not provided</strong>
              <p>No budget threshold or spend warning data was included in the source plan.</p>
            </div>
          </div>
        </article>

        <article className="hero-progress glass-panel">
          <div className="section-title">
            <span className="eyebrow">Milestone Progress</span>
            <h2>Execution Horizon</h2>
          </div>

          <div className="progress-metric">
            <div>
              <span className="metric-caption">Overall Completion</span>
              <strong>0%</strong>
            </div>
            <span className="metric-caption">Target: Not provided</span>
          </div>

          <div className="progress-track" aria-label="Project milestone progress">
            <div className="progress-fill" style={{ width: '0%' }} />
          </div>

          <div className="milestone-list">
            {milestones.map((item) => (
              <div className="milestone-item" key={item.name}>
                <span className="milestone-name">{item.name}</span>
                <span className={`status-pill ${item.tone === 'complete' ? 'status-complete' : 'status-planning'}`}>
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="kpi-grid">
        {kpiCards.map((card) => (
          <article key={card.title} className="kpi-card surface-panel">
            <span className="eyebrow">{card.label}</span>
            <strong>{card.title}</strong>
            <p>{card.description}</p>
            <Link to={card.route} className="button button-secondary kpi-action">
              {card.actionLabel}
            </Link>
          </article>
        ))}
      </section>

      <section className="content-grid">
        <section className="task-board glass-panel">
          <div className="section-title">
            <span className="eyebrow">Task Breakdown</span>
            <h2>Execution Board</h2>
          </div>

          <div className="kanban-grid">
            <article className="kanban-column surface-panel">
              <div className="column-header">
                <h3>Backlog</h3>
                <span className="column-count">N/A</span>
              </div>
              <div className="task-card priority-medium">
                <span className="task-priority">Source Placeholder</span>
                <h4>No backlog tasks were included</h4>
                <p>The provided files do not contain a real backlog list, owner, or due date.</p>
              </div>
            </article>

            <article className="kanban-column surface-panel">
              <div className="column-header">
                <h3>In Progress</h3>
                <span className="column-count">N/A</span>
              </div>
              <div className="task-card priority-high">
                <span className="task-priority">Known Screen Work</span>
                <h4>Aardvark Intelligence 3D Landing Page</h4>
                <p>The only explicit screen currently included in the source package.</p>
              </div>
            </article>

            <article className="kanban-column surface-panel">
              <div className="column-header">
                <h3>Complete</h3>
                <span className="column-count">2</span>
              </div>
              <div className="task-card priority-low">
                <span className="task-priority">Resolved Source Facts</span>
                <h4>Project identity extracted</h4>
                <p>Project title, ID, and screen metadata were mapped from the source design package.</p>
              </div>
            </article>
          </div>
        </section>

        <aside className="timeline-panel glass-panel">
          <div className="section-title">
            <span className="eyebrow">Timeline Widget</span>
            <h2>Delivery Path</h2>
          </div>

          <div className="timeline-list">
            {timelineEntries.map((entry) => (
              <article className="timeline-item" key={`${entry.state}-${entry.title}`}>
                <span className="timeline-date">{entry.state}</span>
                <div className="timeline-content surface-panel">
                  <h3>{entry.title}</h3>
                  <p>{entry.description}</p>
                </div>
              </article>
            ))}
          </div>
        </aside>
      </section>
    </main>
  </section>
);
};

export default DashboardPage;
