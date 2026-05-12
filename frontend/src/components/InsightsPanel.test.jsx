import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import InsightsPanel from './InsightsPanel';

const sampleData = [
  { name: 'Clinic A', city: 'Riyadh', phone: '+9661', email: 'a@example.com', category: 'Dental' },
  { name: 'Clinic B', city: 'Riyadh', phone: '+9662', email: '', category: 'Dental' },
  { name: 'Clinic C', city: 'Jeddah', phone: '+9663', email: '', category: 'General' },
  { name: 'Clinic D', city: 'Jeddah', phone: '+9664', email: '', category: 'General' },
  { name: 'Clinic E', city: 'Dammam', phone: '+9665', email: 'e@example.com', category: 'General' },
];

describe('InsightsPanel', () => {
  test('renders all insight sections when data is available', () => {
    render(
      <InsightsPanel
        data={sampleData}
        sources={[{ name: 'google', count: 3 }, { name: 'directories', count: 2 }]}
        quality={{ coverage: 0.8, confidence: 0.85, duplicates_removed: 1 }}
        missingFields={{ email: 3, website: 2 }}
        total={5}
      />
    );

    expect(screen.getByText('Key Findings')).toBeInTheDocument();
    expect(screen.getByText('Data Quality')).toBeInTheDocument();
    expect(screen.getByText('Observations')).toBeInTheDocument();
    expect(screen.getByText('Data Gaps')).toBeInTheDocument();
    expect(screen.getByText('Suggested Actions')).toBeInTheDocument();
  });

  test('limits each section to a maximum of 4 bullets', () => {
    render(
      <InsightsPanel
        data={sampleData}
        sources={[{ name: 'google', count: 3 }, { name: 'directories', count: 2 }]}
        quality={{ coverage: 0.8, confidence: 0.85, duplicates_removed: 1 }}
        missingFields={{ email: 3, website: 2, address: 2, hours: 1, owner: 1, note: 1 }}
        total={5}
      />
    );

    ['Key Findings', 'Data Quality', 'Observations', 'Data Gaps', 'Suggested Actions'].forEach((title) => {
      const heading = screen.getByText(title);
      const card = heading.closest('div.rounded-xl');
      const listItems = within(card).getAllByRole('listitem');
      expect(listItems.length).toBeLessThanOrEqual(4);
    });
  });

  test('shows fallback when no data is available', () => {
    render(<InsightsPanel data={[]} sources={[]} quality={{}} missingFields={{}} total={0} />);

    expect(screen.getByText('No insights available yet.')).toBeInTheDocument();
  });

  test('supports collapse and expand', () => {
    render(<InsightsPanel data={sampleData} sources={[]} quality={{ coverage: 0.7, confidence: 0.8 }} missingFields={{}} total={5} />);

    fireEvent.click(screen.getByRole('button', { name: /Collapse/i }));
    expect(screen.queryByText('Key Findings')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Expand/i }));
    expect(screen.getByText('Key Findings')).toBeInTheDocument();
  });
});
