import React from 'react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import Sidebar from './Sidebar';

const LocationProbe = () => {
  const location = useLocation();
  return <p data-testid="location-path">{location.pathname}</p>;
};

describe('Sidebar navigation', () => {
  test('updates route when a sidebar link is clicked', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Sidebar />
        <LocationProbe />
      </MemoryRouter>
    );

    expect(screen.getByTestId('location-path')).toHaveTextContent('/dashboard');
    fireEvent.click(screen.getByRole('link', { name: 'History' }));
    expect(screen.getByTestId('location-path')).toHaveTextContent('/history');
  });

  test('renders mobile drawer and closes via close button', () => {
    const onClose = jest.fn();

    render(
      <MemoryRouter>
        <Sidebar mobile open onClose={onClose} />
      </MemoryRouter>
    );

    expect(screen.getByRole('dialog', { name: 'Navigation menu' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close navigation' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
