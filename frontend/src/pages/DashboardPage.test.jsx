import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import DashboardPage from './DashboardPage';
import api from '../services/api';

jest.mock('../services/api', () => ({
  __esModule: true,
  default: {
    getJobs: jest.fn(),
    getRuns: jest.fn(),
    getAccountSummary: jest.fn(),
    getResults: jest.fn(),
    createJob: jest.fn(),
    startJobRun: jest.fn(),
  },
}));

jest.mock('../components/AICommandPanel', () => ({
  __esModule: true,
  default: ({ initialUrl, initialPrompt, onStart }) => (
    <div>
      <div>AI Command Panel</div>
      <div data-testid="initial-url">{initialUrl}</div>
      <div data-testid="initial-prompt">{initialPrompt}</div>
      <button
        type="button"
        onClick={() =>
          onStart(
            {
              url: initialUrl || 'https://example.com/catalog',
              scrape_type: 'structured',
            },
            initialPrompt || 'Find product prices'
          )
        }
      >
        Review and Run
      </button>
    </div>
  ),
}));

jest.mock('../components/QuickStatusCards', () => ({
  __esModule: true,
  default: () => <div>Quick Status Cards</div>,
}));

jest.mock('../components/ResultsWorkbench', () => ({
  __esModule: true,
  default: () => <div>Results Workbench</div>,
}));

jest.mock('../components/RecentRunsCard', () => ({
  __esModule: true,
  default: () => <div>Recent Runs Card</div>,
}));

jest.mock('../components/RecentRequestsCard', () => ({
  __esModule: true,
  default: () => <div>Recent Requests Card</div>,
}));

describe('DashboardPage landing intent flow', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    api.getJobs.mockResolvedValue([]);
    api.getRuns.mockResolvedValue([]);
    api.getAccountSummary.mockResolvedValue({
      plan: { plan: 'free', max_jobs: 5, max_runs_per_day: 10 },
      usage: { total_jobs: 0, total_runs: 0, total_exports: 0, runs_today: 0 },
    });
    api.getResults.mockResolvedValue([]);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('hydrates the dashboard command panel from landing intent', async () => {
    sessionStorage.setItem(
      'landing_extraction_intent',
      JSON.stringify({
        url: 'https://example.com/catalog',
        prompt: 'Find product prices',
        requiresLogin: false,
      })
    );

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText('AI Command Panel')).toBeInTheDocument());
    expect(screen.getByTestId('initial-url')).toHaveTextContent('https://example.com/catalog');
    expect(screen.getByTestId('initial-prompt')).toHaveTextContent('Find product prices');
    expect(sessionStorage.getItem('landing_extraction_intent')).toBeNull();
  });

  test('redirects protected landing intents to the new-job flow', async () => {
    sessionStorage.setItem(
      'landing_extraction_intent',
      JSON.stringify({
        url: 'https://example.com/private',
        prompt: 'Extract protected content',
        requiresLogin: true,
        login_url: 'https://example.com/login',
        login_username: 'demo@example.com',
        login_password: 'super-secret',
      })
    );

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/jobs/new" element={<div>New Job Route</div>} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText('New Job Route')).toBeInTheDocument());
    expect(sessionStorage.getItem('landing_extraction_intent')).not.toBeNull();
  });

  test('routes dashboard requests through the shared new-job flow', async () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/jobs/new" element={<div>New Job Route</div>} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText('AI Command Panel')).toBeInTheDocument());
    screen.getByRole('button', { name: /review and run/i }).click();

    await waitFor(() => expect(screen.getByText('New Job Route')).toBeInTheDocument());
    expect(JSON.parse(sessionStorage.getItem('landing_extraction_intent'))).toMatchObject({
      url: 'https://example.com/catalog',
      prompt: 'Find product prices',
      scrape_type: 'structured',
      max_pages: 10,
      follow_pagination: true,
      requiresLogin: false,
    });
  });
});
