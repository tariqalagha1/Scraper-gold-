import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import LoginPage from './LoginPage';
import { useAuth } from '../context/AuthContext';

jest.mock('../context/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../services/api', () => ({
  extractApiErrorMessage: jest.fn((err, fallback) => err?.response?.data?.detail || fallback),
}));

describe('LoginPage', () => {
  const login = jest.fn();
  const register = jest.fn();
  const getSubmitButton = () => screen.getAllByRole('button', { name: /^login$/i }).at(-1);

  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      login,
      register,
    });
  });

  test('shows a normalized validation message for empty login fields', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.click(getSubmitButton());

    expect(await screen.findByText('Enter a valid email and password to sign in.')).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });

  test('normalizes backend 422 responses for login attempts', async () => {
    login.mockRejectedValue({
      response: {
        status: 422,
        data: {
          detail: [{ msg: 'Field required' }],
        },
      },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'demo@example.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'secret123' } });
    fireEvent.click(getSubmitButton());

    expect(await screen.findByText('Enter a valid email and password to sign in.')).toBeInTheDocument();
  });

  test('redirects to the dashboard after a successful login', async () => {
    login.mockResolvedValue({ success: true });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<div>Dashboard Route</div>} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'demo@example.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'secret123' } });
    fireEvent.click(getSubmitButton());

    await waitFor(() => expect(screen.getByText('Dashboard Route')).toBeInTheDocument());
    expect(login).toHaveBeenCalledWith('demo@example.com', 'secret123');
  });

  test('shows the backend offline message returned by register', async () => {
    register.mockResolvedValue({
      success: false,
      error: 'Cannot reach the API server at http://127.0.0.1:8000/api/v1. Start the backend and try again.',
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'demo@example.com' } });
    fireEvent.change(screen.getAllByLabelText(/password/i)[0], { target: { value: 'secret123' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'secret123' } });
    fireEvent.click(screen.getAllByRole('button', { name: /create account/i }).at(-1));

    expect(
      await screen.findByText(
        'Cannot reach the API server at http://127.0.0.1:8000/api/v1. Start the backend and try again.'
      )
    ).toBeInTheDocument();
  });
});
