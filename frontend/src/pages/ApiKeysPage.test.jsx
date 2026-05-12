import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import ApiKeysPage from './ApiKeysPage';
import api from '../services/api';

jest.mock('../services/api', () => ({
  __esModule: true,
  default: {
    getApiKeys: jest.fn(),
    createApiKey: jest.fn(),
    deleteApiKey: jest.fn(),
  },
  API_KEY_HEADER_NAME: 'X-API-Key',
  extractApiErrorMessage: (error, fallback = 'An error occurred') =>
    error?.response?.data?.detail || fallback,
}));

const renderApiKeysPage = () =>
  render(
    <MemoryRouter>
      <ApiKeysPage />
    </MemoryRouter>
  );

describe('ApiKeysPage hardening', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    api.getApiKeys.mockResolvedValue([]);
    api.createApiKey.mockResolvedValue({
      id: 'key-2',
      name: 'Integration',
      api_key: 'ss_new_key_123',
      key: 'ss_new_key_123',
    });
    api.deleteApiKey.mockResolvedValue(null);
  });

  test('has labeled input and create action', async () => {
    renderApiKeysPage();
    await waitFor(() => expect(api.getApiKeys).toHaveBeenCalled());

    expect(screen.getByLabelText('Key name')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create key' })).toBeInTheDocument();
  });

  test('blocks API key creation when name is blank after trim', async () => {
    renderApiKeysPage();
    await waitFor(() => expect(api.getApiKeys).toHaveBeenCalled());

    fireEvent.change(screen.getByLabelText('Key name'), { target: { value: '    ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create key' }));

    expect(api.createApiKey).not.toHaveBeenCalled();
    expect(screen.getByText('Key name is required.')).toBeInTheDocument();
  });

  test('prevents duplicate create clicks while request is running', async () => {
    let resolveCreate;
    api.createApiKey.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreate = resolve;
        })
    );

    renderApiKeysPage();
    await waitFor(() => expect(api.getApiKeys).toHaveBeenCalled());

    fireEvent.change(screen.getByLabelText('Key name'), { target: { value: 'Integration key' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create key' }));
    fireEvent.click(screen.getByRole('button', { name: 'Creating...' }));

    await waitFor(() => expect(api.createApiKey).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('button', { name: 'Creating...' })).toBeDisabled();

    resolveCreate({
      id: 'key-3',
      name: 'Integration key',
      api_key: 'ss_created_key_1',
      key: 'ss_created_key_1',
    });

    await waitFor(() => expect(screen.getByRole('button', { name: 'Create key' })).toBeInTheDocument());
    expect(await screen.findByRole('button', { name: 'Copy key' })).toBeInTheDocument();
  });

  test('asks for confirmation before revoking a key', async () => {
    api.getApiKeys.mockResolvedValue([
      {
        id: 'key-1',
        name: 'Primary',
        key_preview: 'ss_ab...1234',
        created_at: '2026-01-01T00:00:00.000Z',
      },
    ]);
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false);

    renderApiKeysPage();
    await waitFor(() => expect(screen.getByText('Primary')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Revoke' }));

    expect(confirmSpy).toHaveBeenCalledWith('Revoke this API key?');
    expect(api.deleteApiKey).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });
});
