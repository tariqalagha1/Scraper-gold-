import React from 'react';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import LandingPage from './LandingPage';

const mockUseAuth = jest.fn();

jest.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

describe('LandingPage', () => {
  beforeEach(() => {
    sessionStorage.clear();
    mockUseAuth.mockReturnValue({ isAuthenticated: false });
  });

  test('stores anonymous extraction intent and routes to login', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<div>Login Route</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('See the scraping run unfold, not just the final answer')).toBeInTheDocument();
    expect(screen.getByText('extract_records()')).toBeInTheDocument();

    await userEvent.clear(screen.getByPlaceholderText('https://books.toscrape.com/catalogue/category/books/travel_2/index.html'));
    await userEvent.type(screen.getByPlaceholderText('https://books.toscrape.com/catalogue/category/books/travel_2/index.html'), 'https://example.com/private');
    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.type(screen.getByPlaceholderText('Login URL (optional)'), 'https://example.com/login');
    await userEvent.type(screen.getByPlaceholderText('Username or email'), 'demo@example.com');
    await userEvent.type(screen.getByPlaceholderText('Password'), 'super-secret');
    await userEvent.click(screen.getByRole('button', { name: /run extraction/i }));

    expect(screen.getByText('Login Route')).toBeInTheDocument();
    expect(JSON.parse(sessionStorage.getItem('landing_extraction_intent'))).toMatchObject({
      url: 'https://example.com/private',
      prompt: 'Extract structured product data',
      requiresLogin: true,
      login_url: 'https://example.com/login',
      login_username: 'demo@example.com',
      login_password: '',
    });
  });

  test('preserves protected-site password for authenticated users and routes to dashboard', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<div>Dashboard Route</div>} />
        </Routes>
      </MemoryRouter>
    );

    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.type(screen.getByPlaceholderText('Password'), 'super-secret');
    await userEvent.click(screen.getByRole('button', { name: /run extraction/i }));

    expect(screen.getByText('Dashboard Route')).toBeInTheDocument();
    expect(JSON.parse(sessionStorage.getItem('landing_extraction_intent'))).toMatchObject({
      prompt: 'Extract structured product data',
      requiresLogin: true,
      login_password: 'super-secret',
    });
  });
});
