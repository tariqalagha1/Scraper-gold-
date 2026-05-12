import React from 'react';
import { render, screen } from '@testing-library/react';
import ResultsWorkbench from './ResultsWorkbench';

describe('ResultsWorkbench failed envelopes', () => {
  test('does not count failed result wrappers as extracted records', () => {
    render(
      <ResultsWorkbench
        results={[
          {
            data_json: {
              items: [],
              status: 'failed',
              result: {
                data: [],
                processed: { items: [] },
              },
              errors: ['Cannot reach Smart Scraper service.'],
            },
          },
        ]}
      />
    );

    expect(screen.getByText('No results yet')).toBeInTheDocument();
  });
});
