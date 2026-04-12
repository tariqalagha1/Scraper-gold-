import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import SettingsPage from './SettingsPage';
import api from '../services/api';

jest.mock('../services/api', () => ({
  __esModule: true,
  default: {
    getStorageCleanupSummary: jest.fn(),
    clearHistory: jest.fn(),
    clearTempFiles: jest.fn(),
    clearAllUserData: jest.fn(),
  },
}));

describe('SettingsPage', () => {
  const originalLocation = window.location;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem('access_token', 'test-token');
    localStorage.setItem('user', JSON.stringify({ email: 'cleanup@example.com' }));
    localStorage.setItem('recent_requests', JSON.stringify([{ id: 1, url: 'https://example.com' }]));
    sessionStorage.setItem('landing_extraction_intent', JSON.stringify({ url: 'https://example.com' }));
    delete window.location;
    window.location = { href: 'http://localhost/settings' };

    api.getStorageCleanupSummary.mockResolvedValue({
      history: { total_records: 4 },
      temp_files: { total_files: 7, estimated_freed_space_mb: 3.2 },
    });
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    window.location = originalLocation;
  });

  test('opens the confirmation modal and clears history', async () => {
    api.clearHistory.mockResolvedValue({
      status: 'success',
      deleted_items_count: 4,
      freed_space_mb: 3.2,
    });

    render(<SettingsPage />);

    expect(await screen.findByText('Storage & Privacy')).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getAllByRole('button', { name: 'Clear History' })[0]).not.toBeDisabled()
    );

    fireEvent.click(screen.getAllByRole('button', { name: 'Clear History' })[0]);

    expect(screen.getByText('Are you sure?')).toBeInTheDocument();
    expect(screen.getByText('This action cannot be undone.')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: 'Clear History' }).at(-1));

    await waitFor(() => expect(api.clearHistory).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText(/Clear History completed/i)).toBeInTheDocument());
    expect(localStorage.getItem('recent_requests')).toBeNull();
  });

  test('clear all removes session artifacts and redirects to login', async () => {
    api.clearAllUserData.mockResolvedValue({
      status: 'success',
      deleted_items_count: 11,
      freed_space_mb: 3.2,
    });

    render(<SettingsPage />);

    expect(await screen.findByText('Storage & Privacy')).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getAllByRole('button', { name: 'Clear All' })[0]).not.toBeDisabled()
    );
    fireEvent.click(screen.getAllByRole('button', { name: 'Clear All' })[0]);
    expect(await screen.findByText('Are you sure?')).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: 'Clear All' }).at(-1));

    await waitFor(() => expect(api.clearAllUserData).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByText(/Clear All completed/i)).toBeInTheDocument());

    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
    expect(localStorage.getItem('recent_requests')).toBeNull();
    expect(sessionStorage.getItem('landing_extraction_intent')).toBeNull();

    jest.advanceTimersByTime(300);
    expect(window.location.href).toBe('/login');
  });

  test('double click confirm only submits one clear all request', async () => {
    let resolveRequest;
    api.clearAllUserData.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRequest = resolve;
        })
    );

    render(<SettingsPage />);

    expect(await screen.findByText('Storage & Privacy')).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getAllByRole('button', { name: 'Clear All' })[0]).not.toBeDisabled()
    );
    fireEvent.click(screen.getAllByRole('button', { name: 'Clear All' })[0]);
    expect(await screen.findByText('Are you sure?')).toBeInTheDocument();

    const confirmButton = screen.getAllByRole('button', { name: 'Clear All' }).at(-1);
    fireEvent.click(confirmButton);
    fireEvent.click(confirmButton);

    await waitFor(() => expect(api.clearAllUserData).toHaveBeenCalledTimes(1));

    resolveRequest({
      status: 'success',
      deleted_items_count: 11,
      freed_space_mb: 3.2,
    });

    await waitFor(() => expect(screen.getByText(/Clear All completed/i)).toBeInTheDocument());
  });

  test('clear all timeout leaves session intact and shows an error', async () => {
    api.clearAllUserData.mockRejectedValue(new Error('Network timeout'));

    render(<SettingsPage />);

    expect(await screen.findByText('Storage & Privacy')).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getAllByRole('button', { name: 'Clear All' })[0]).not.toBeDisabled()
    );
    fireEvent.click(screen.getAllByRole('button', { name: 'Clear All' })[0]);
    expect(await screen.findByText('Are you sure?')).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: 'Clear All' }).at(-1));

    await waitFor(() =>
      expect(screen.getByText(/We could not complete "Clear All" right now\./i)).toBeInTheDocument()
    );

    expect(localStorage.getItem('access_token')).toBe('test-token');
    expect(window.location.href).toBe('http://localhost/settings');
  });
});
