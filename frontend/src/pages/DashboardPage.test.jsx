import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import DashboardPage from './DashboardPage';
import api from '../services/api';

jest.mock('../services/api', () => ({
  __esModule: true,
  extractApiErrorMessage: jest.fn((error, fallback) => fallback || 'An error occurred'),
  default: {
    getDashboardPreferences: jest.fn(),
    getSystemCapabilities: jest.fn(),
    updateDashboardPreferences: jest.fn(),
    refineScrapeRequest: jest.fn(),
    createJob: jest.fn(),
    startJobRun: jest.fn(),
  },
}));

const renderDashboard = () =>
  render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <DashboardPage />
    </MemoryRouter>
  );

describe('DashboardPage command center UX', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    api.getDashboardPreferences.mockResolvedValue({
      preferences: {
        visibility: 'Internal Only',
        category_filter: 'All Workstreams',
        notifications: {
          budget_warnings: true,
          overdue_tasks: true,
          milestone_alerts: true,
          executive_digest: false,
        },
        plan_tags: ['Active', 'AI Infra'],
      },
      updated_at: '2026-05-03T09:00:00Z',
    });
    api.updateDashboardPreferences.mockImplementation(async (payload) => ({
      preferences: payload,
      updated_at: '2026-05-03T09:01:00Z',
    }));
    api.getSystemCapabilities.mockResolvedValue({
      execution_contract: {
        agents: [
          'policy_service',
          'strategic_execution_service',
          'multi_source_service',
          'quality_layer',
          'event_emitter',
          'control_service',
        ],
        optional_agents: ['analysis_agent', 'vector_agent', 'export_agent'],
        execution_modes: ['single_source', 'multi_source'],
        sources: ['internal', 'google_maps', 'web'],
        limit: { min: 1, max: 100, default: 50 },
        controls: { fallback: true, early_stop: true, retry: true },
      },
    });
    api.refineScrapeRequest.mockResolvedValue({
      assistant_message: 'I can tighten this into a structured extraction brief.',
      refined_prompt: 'Collect title, price, and availability from each listing page.',
      recommended_scrape_type: 'structured',
      clarifying_questions: [],
    });
    api.createJob.mockResolvedValue({ id: 42 });
    api.startJobRun.mockResolvedValue({ id: 1001, status: 'running' });
  });

  test('renders command center heading and separate settings controls', () => {
    renderDashboard();

    expect(screen.getByRole('heading', { name: 'Command Center' })).toBeInTheDocument();
    expect(screen.getByText('Project Settings')).toBeInTheDocument();
    expect(screen.getByLabelText('Visibility')).toBeInTheDocument();
    expect(screen.getByLabelText('Category Filter')).toBeInTheDocument();
    expect(screen.getByText('Notifications')).toBeInTheDocument();
    expect(screen.getByText('Plan Tags')).toBeInTheDocument();
  });

  test('loads and persists dashboard preferences', async () => {
    renderDashboard();

    expect(await screen.findByDisplayValue('Internal Only')).toBeInTheDocument();
    const budgetWarningsToggle = await screen.findByRole('checkbox', { name: 'Budget Warnings' });
    await waitFor(() => expect(budgetWarningsToggle).not.toBeDisabled());

    fireEvent.click(budgetWarningsToggle);

    await waitFor(() => {
      const lastCallPayload = api.updateDashboardPreferences.mock.calls.at(-1)?.[0];
      expect(lastCallPayload).toEqual(
        expect.objectContaining({
          notifications: expect.objectContaining({ budget_warnings: false }),
        })
      );
    });
  });

  test('surfaces main feature cards and navigation actions', () => {
    renderDashboard();

    expect(screen.getByRole('heading', { name: 'Execution Board' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Delivery Path' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open Integrations' })).toHaveAttribute('href', '/ai-integrations');
    expect(screen.getByRole('link', { name: 'Open API Keys' })).toHaveAttribute('href', '/api-keys');
    expect(screen.getByRole('link', { name: 'Open Workspace' })).toHaveAttribute('href', '/workspace');
    expect(screen.getByRole('link', { name: 'Open Settings' })).toHaveAttribute('href', '/settings');
  });

  test('shows core workflow inputs for website, request, and credentials toggle', () => {
    renderDashboard();

    expect(screen.getByRole('heading', { name: 'Website + Credentials + AI' })).toBeInTheDocument();
    expect(screen.getByLabelText('Website URL')).toBeInTheDocument();
    expect(screen.getByLabelText('AI Request')).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Website requires login' })).toBeInTheDocument();
  });

  test('starts a run from dashboard workflow when required fields are provided', async () => {
    renderDashboard();

    fireEvent.change(screen.getByLabelText('Website URL'), {
      target: { value: 'https://books.toscrape.com' },
    });
    fireEvent.change(screen.getByLabelText('AI Request'), {
      target: { value: 'Collect product title and price from listing pages.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Create Job & Start Run' }));

    await waitFor(() => {
      expect(api.createJob).toHaveBeenCalledWith(
        expect.objectContaining({
          url: 'https://books.toscrape.com',
          prompt: 'Collect product title and price from listing pages.',
          login_url: null,
          login_username: null,
          login_password: null,
        })
      );
    });
    await waitFor(() => {
      expect(api.startJobRun).toHaveBeenCalledWith(
        42,
        expect.objectContaining({
          executionContract: expect.objectContaining({
            execution_mode: 'single_source',
            sources: ['web'],
            controls: expect.objectContaining({
              fallback: true,
              early_stop: true,
              retry: true,
            }),
          }),
          job: expect.objectContaining({ id: 42 }),
        })
      );
    });
  });
});
