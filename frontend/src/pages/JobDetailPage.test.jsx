import React, { act } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import JobDetailPage from './JobDetailPage';
import api from '../services/api';

jest.mock('../services/api', () => ({
  __esModule: true,
  default: {
    getJob: jest.fn(),
    getRunsByJob: jest.fn(),
    getResults: jest.fn(),
    getRunLogs: jest.fn(),
    startJobRun: jest.fn(),
    retryRun: jest.fn(),
    createExport: jest.fn(),
  },
}));

describe('JobDetailPage', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    api.getJob.mockResolvedValue({
      id: 'job-1',
      url: 'https://example.com',
      scrape_type: 'general',
      status: 'pending',
      created_at: '2026-03-22T12:00:00+00:00',
    });
    api.getResults.mockResolvedValue([]);
    api.getRunLogs.mockResolvedValue([]);
    api.createExport.mockResolvedValue({ id: 'export-1' });
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  const renderPage = async () => {
    await act(async () => {
      render(
        <MemoryRouter
          initialEntries={['/jobs/job-1']}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
        <Routes>
          <Route path="/jobs/:id" element={<JobDetailPage />} />
        </Routes>
        </MemoryRouter>
      );
    });
  };

  test('renders latest run progress safely and polls while active', async () => {
    api.getRunsByJob.mockResolvedValue([
      {
        id: 'run-1',
        job_id: 'job-1',
        status: 'running',
        progress: 55,
        started_at: '2026-03-22T12:01:00+00:00',
        finished_at: null,
        error_message: null,
        created_at: '2026-03-22T12:01:00+00:00',
      },
    ]);

    await renderPage();

    await waitFor(() => expect(screen.getByText('Execution Trace')).toBeInTheDocument());
    expect(screen.getByText('Decision')).toBeInTheDocument();
    expect(screen.getByText('Behind-the-scenes execution graph')).toBeInTheDocument();
    expect(screen.getByText('extract_records()')).toBeInTheDocument();
    expect(screen.getByText('Validation Result')).toBeInTheDocument();
    expect(screen.getByText('Retry Explanation')).toBeInTheDocument();
    expect(screen.getByText('Memory Usage')).toBeInTheDocument();
    expect(screen.getAllByText('55%').length).toBeGreaterThan(0);
    expect(api.getRunsByJob).toHaveBeenCalledWith('job-1');

    await act(async () => {
      jest.advanceTimersByTime(4000);
    });

    expect(api.getRunsByJob).toHaveBeenCalledTimes(2);
  });

  test('starts a run using the real API method', async () => {
    api.getRunsByJob.mockResolvedValueOnce([
      {
        id: 'run-0',
        job_id: 'job-1',
        status: 'completed',
        progress: 100,
        started_at: '2026-03-22T12:01:00+00:00',
        finished_at: '2026-03-22T12:05:00+00:00',
        error_message: null,
        created_at: '2026-03-22T12:05:00+00:00',
      },
    ]).mockResolvedValue([
      {
        id: 'run-1',
        job_id: 'job-1',
        status: 'pending',
        progress: 0,
        started_at: null,
        finished_at: null,
        error_message: null,
        created_at: '2026-03-22T12:06:00+00:00',
      },
    ]);
    api.startJobRun.mockResolvedValue({
      id: 'run-1',
      job_id: 'job-1',
      status: 'pending',
      progress: 0,
      started_at: null,
      finished_at: null,
      error_message: null,
      created_at: '2026-03-22T12:06:00+00:00',
    });

    await renderPage();

    await waitFor(() => expect(screen.getByRole('button', { name: 'Start Run' })).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Start Run' }));
    });

    await waitFor(() => expect(api.startJobRun).toHaveBeenCalledWith('job-1'));
    expect(api.getRunsByJob).toHaveBeenCalledTimes(2);
  });

  test('shows retry button for failed runs and calls retryRun', async () => {
    api.getRunsByJob.mockResolvedValue([
      {
        id: 'run-failed',
        job_id: 'job-1',
        status: 'failed',
        progress: 100,
        started_at: '2026-03-22T12:01:00+00:00',
        finished_at: '2026-03-22T12:05:00+00:00',
        error_message: 'Readable failure',
        created_at: '2026-03-22T12:05:00+00:00',
      },
    ]);
    api.retryRun.mockResolvedValue({
      id: 'run-retry',
      job_id: 'job-1',
      status: 'pending',
      progress: 0,
      started_at: null,
      finished_at: null,
      error_message: null,
      created_at: '2026-03-22T12:06:00+00:00',
    });

    await renderPage();

    await waitFor(() => expect(screen.getByRole('button', { name: 'Retry Run' })).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Retry Run' }));
    });

    await waitFor(() => expect(api.retryRun).toHaveBeenCalledWith('run-failed'));
  });

  test('renders human friendly live steps from logs', async () => {
    api.getRunsByJob.mockResolvedValue([
      {
        id: 'run-1',
        job_id: 'job-1',
        status: 'completed',
        progress: 100,
        started_at: '2026-03-22T12:01:00+00:00',
        finished_at: '2026-03-22T12:05:00+00:00',
        error_message: null,
        created_at: '2026-03-22T12:05:00+00:00',
      },
    ]);
    api.getRunLogs.mockResolvedValue([
      {
        timestamp: '2026-03-22T12:02:00+00:00',
        event: 'pipeline_started',
        message: 'Pipeline execution started.',
      },
    ]);

    await renderPage();

    await waitFor(() => expect(screen.getByText('Structured extraction completed')).toBeInTheDocument());
  });
});
