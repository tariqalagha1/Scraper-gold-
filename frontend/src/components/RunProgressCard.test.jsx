import { buildNodeState } from './RunProgressCard';

describe('RunProgressCard node state', () => {
  test('ignores post-failure completion logs for failed runs', () => {
    const state = buildNodeState(
      [
        { event: 'node_completed', details: { node: 'intake' } },
        { event: 'node_completed', details: { node: 'scraper' } },
        { event: 'node_completed', details: { node: 'processing' } },
        { event: 'node_completed', details: { node: 'vector' } },
        { event: 'node_started', details: { node: 'analysis' } },
        { event: 'run_failed', level: 'error', message: 'Cannot reach Smart Scraper service.' },
        { event: 'node_completed', details: { node: 'analysis' } },
        { event: 'node_completed', details: { node: 'export' } },
      ],
      'failed'
    );

    expect(state.intake).toBe('completed');
    expect(state.scraper).toBe('completed');
    expect(state.processing).toBe('completed');
    expect(state.vector).toBe('completed');
    expect(state.analysis).toBe('failed');
    expect(state.export).toBe('pending');
  });
});
