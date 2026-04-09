import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NewJobPage from './NewJobPage';
import api from '../services/api';

jest.mock('../services/api', () => ({
  __esModule: true,
  default: {
    createJob: jest.fn(),
    startJobRun: jest.fn(),
  },
}));

describe('NewJobPage landing intent flow', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    api.createJob.mockResolvedValue({ id: 'job-123' });
    api.startJobRun.mockResolvedValue({ id: 'run-456' });
  });

  test('hydrates target-site login details from the landing intent', async () => {
    sessionStorage.setItem(
      'landing_extraction_intent',
      JSON.stringify({
        url: 'https://example.com/private',
        prompt: 'Find product prices in the protected catalog',
        max_pages: 25,
        follow_pagination: false,
        requiresLogin: true,
        login_url: 'https://example.com/login',
        login_username: 'demo@example.com',
        login_password: 'super-secret',
      })
    );

    render(
      <MemoryRouter>
        <NewJobPage />
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(screen.getByDisplayValue('https://example.com/private')).toBeInTheDocument()
    );

    userEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() =>
      expect(screen.getByRole('radio', { name: /structured data/i })).toBeChecked()
    );

    userEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() =>
      expect(screen.getByRole('checkbox', { name: /site requires login/i })).toBeChecked()
    );
    expect(screen.getByDisplayValue('25')).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: /follow pagination links/i })).not.toBeChecked();
    expect(screen.getByDisplayValue('https://example.com/login')).toBeInTheDocument();
    expect(screen.getByDisplayValue('demo@example.com')).toBeInTheDocument();
    expect(screen.getByDisplayValue('super-secret')).toBeInTheDocument();
    expect(sessionStorage.getItem('landing_extraction_intent')).toBeNull();
  });

  test('creates the job and starts the first run on submit', async () => {
    sessionStorage.setItem(
      'landing_extraction_intent',
      JSON.stringify({
        url: 'https://example.com/private',
        prompt: 'Find product prices in the protected catalog',
        requiresLogin: true,
        scrape_type: 'structured',
        max_pages: 25,
        follow_pagination: false,
        login_url: 'https://example.com/login',
        login_username: 'demo@example.com',
        login_password: 'super-secret',
      })
    );

    render(
      <MemoryRouter initialEntries={['/jobs/new']}>
        <Routes>
          <Route path="/jobs/new" element={<NewJobPage />} />
          <Route path="/jobs/:id" element={<div>Job Detail Route</div>} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(screen.getByDisplayValue('https://example.com/private')).toBeInTheDocument()
    );

    userEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() =>
      expect(screen.getByRole('radio', { name: /structured data/i })).toBeChecked()
    );

    userEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() =>
      expect(screen.getByRole('checkbox', { name: /site requires login/i })).toBeChecked()
    );

    userEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => expect(screen.getByText(/review your job/i)).toBeInTheDocument());

    userEvent.click(screen.getByRole('button', { name: /create job & start run/i }));

    await waitFor(() =>
      expect(api.createJob).toHaveBeenCalledWith({
        url: 'https://example.com/private',
        prompt: 'Find product prices in the protected catalog',
        login_url: 'https://example.com/login',
        login_username: 'demo@example.com',
        login_password: 'super-secret',
        scrape_type: 'structured',
        max_pages: 25,
        follow_pagination: false,
      })
    );
    await waitFor(() => expect(api.startJobRun).toHaveBeenCalledWith('job-123'));
    await waitFor(() => expect(screen.getByText('Job Detail Route')).toBeInTheDocument());
    expect(JSON.parse(localStorage.getItem('recent_requests'))).toEqual([
      expect.objectContaining({
        url: 'https://example.com/private',
        prompt: 'Find product prices in the protected catalog',
        scrape_type: 'structured',
        max_pages: 25,
        follow_pagination: false,
        title: 'Find product prices in the protected catalog',
      }),
    ]);
  });

  test('blocks submit when the target URL is invalid', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs/new']}>
        <Routes>
          <Route path="/jobs/new" element={<NewJobPage />} />
        </Routes>
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/url to scrape/i), 'notaurl');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => expect(screen.getByText(/review your job/i)).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /create job & start run/i }));

    expect(await screen.findByText(/enter a valid http:\/\/ or https:\/\/ url\./i)).toBeInTheDocument();
    expect(api.createJob).not.toHaveBeenCalled();
    expect(api.startJobRun).not.toHaveBeenCalled();
  });

  test('blocks protected-page jobs when login credentials are incomplete', async () => {
    render(
      <MemoryRouter initialEntries={['/jobs/new']}>
        <Routes>
          <Route path="/jobs/new" element={<NewJobPage />} />
        </Routes>
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/url to scrape/i), 'https://example.com/private');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await userEvent.click(screen.getByRole('button', { name: /next/i }));

    await userEvent.click(screen.getByRole('checkbox', { name: /site requires login/i }));
    await userEvent.type(screen.getByLabelText(/login url/i), 'https://example.com/login');
    await userEvent.type(screen.getByLabelText(/username \/ email/i), 'demo@example.com');

    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => expect(screen.getByText(/review your job/i)).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /create job & start run/i }));

    expect(await screen.findByText(/enter the login url, username, and password for protected pages\./i)).toBeInTheDocument();
    expect(api.createJob).not.toHaveBeenCalled();
  });
});
