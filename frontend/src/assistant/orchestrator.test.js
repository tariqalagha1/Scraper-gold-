import {
  buildActivityFeed,
  buildResultSummary,
  buildRunExplanation,
  buildWorkspaceHealth,
  detectScrapeType,
  interpretCommand,
} from './orchestrator';

describe('assistant orchestrator', () => {
  test('detects structured intent from plain english', () => {
    expect(detectScrapeType('Get all product prices from this website')).toBe('structured');
    expect(detectScrapeType('Download all PDFs')).toBe('pdf');
    expect(detectScrapeType('Find images from the gallery')).toBe('images');
  });

  test('builds command preview from intent', () => {
    expect(
      interpretCommand({
        url: 'https://example.com',
        prompt: 'Get all product prices from this website',
      })
    ).toMatchObject({
      url: 'https://example.com',
      scrape_type: 'structured',
      title: 'Get all product prices from this website',
    });
  });

  test('builds readable result summary', () => {
    expect(
      buildResultSummary([
        { data_json: { price: '$10' } },
        { data_json: { price: '$45' } },
      ])
    ).toContain('Most prices appear to fall between $10 and $45');
  });

  test('builds guided explanation for failed runs', () => {
    const explanation = buildRunExplanation({
      run: { status: 'failed', error_message: 'The website took too long to respond.' },
      results: [],
      logs: [],
    });

    expect(explanation.title).toBe('The run needs attention');
    expect(explanation.nextStep).toContain('Try again');
    expect(explanation.suggestions).toContain('Retry the run');
  });

  test('builds recent activity feed items in newest-first order', () => {
    const feed = buildActivityFeed({
      jobs: [{ id: 'job-1', url: 'https://example.com', scrape_type: 'general', created_at: '2026-03-22T12:00:00Z' }],
      runs: [{ id: 'run-1', job_id: 'job-1', status: 'completed', progress: 100, finished_at: '2026-03-23T12:00:00Z' }],
      exports: [{ id: 'export-1', run_id: 'run-1', format: 'excel', file_path: 'exports/run-1.xlsx', created_at: '2026-03-23T13:00:00Z' }],
    });

    expect(feed[0].type).toBe('export');
    expect(feed[1].type).toBe('run');
    expect(feed[2].type).toBe('job');
  });

  test('builds workspace health from run states', () => {
    const health = buildWorkspaceHealth({
      runs: [
        { status: 'completed' },
        { status: 'running' },
        { status: 'failed' },
      ],
    });

    expect(health.label).toBe('Active');
    expect(health.activeRuns).toBe(1);
    expect(health.failedRuns).toBe(1);
  });
});
