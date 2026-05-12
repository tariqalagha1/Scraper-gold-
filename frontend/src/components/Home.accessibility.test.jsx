import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import Home from './Home';

jest.mock('../services/api', () => ({
  __esModule: true,
  default: {
    runScrape: jest.fn(),
    createJob: jest.fn(),
    startJobRun: jest.fn(),
    getRunsByJob: jest.fn(),
    getHealth: jest.fn(),
    getRunLogs: jest.fn(),
    getResults: jest.fn(),
  },
  extractApiErrorMessage: (error, fallback = 'An error occurred') => fallback,
}));

describe('Home accessibility baseline', () => {
  test('includes labeled inputs and accessible buttons', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByLabelText('What do you want to scrape?')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run' })).toBeInTheDocument();

    const advancedToggle = screen.getByRole('button', { name: /Advanced Options/i });
    expect(advancedToggle).toHaveAttribute('aria-expanded', 'false');
  });
});
