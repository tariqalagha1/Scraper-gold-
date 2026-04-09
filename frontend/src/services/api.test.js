jest.mock('axios', () => ({
  create: jest.fn(() => ({
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  })),
  get: jest.fn(),
}));

import axios from 'axios';
import api, { apiClient, extractApiErrorMessage } from './api';

describe('api service', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  test('getJobs unwraps response.data.jobs', async () => {
    apiClient.get.mockResolvedValue({
      data: {
        jobs: [{ id: 'job-1', url: 'https://example.com' }],
        total: 1,
      },
    });

    await expect(api.getJobs()).resolves.toEqual([{ id: 'job-1', url: 'https://example.com' }]);
  });

  test('run methods use real backend contracts', async () => {
    apiClient.post.mockResolvedValue({
      data: { id: 'run-1', job_id: 'job-1', status: 'pending', progress: 0 },
    });
    apiClient.get.mockResolvedValue({
      data: {
        runs: [{ id: 'run-1', job_id: 'job-1', status: 'running', progress: 20 }],
      },
    });

    await expect(api.startJobRun('job-1')).resolves.toEqual(
      expect.objectContaining({
        id: 'run-1',
        job_id: 'job-1',
        status: 'pending',
        progress: 0,
        token_compression_ratio: null,
        stealth_engaged: false,
        markdown_snapshot_path: null,
      })
    );
    await expect(api.getRuns()).resolves.toEqual([
      expect.objectContaining({
        id: 'run-1',
        job_id: 'job-1',
        status: 'running',
        progress: 20,
        token_compression_ratio: null,
        stealth_engaged: false,
        markdown_snapshot_path: null,
      }),
    ]);
    await expect(api.getRunsByJob('job-1')).resolves.toEqual([
      expect.objectContaining({
        id: 'run-1',
        job_id: 'job-1',
        status: 'running',
        progress: 20,
        token_compression_ratio: null,
        stealth_engaged: false,
        markdown_snapshot_path: null,
      }),
    ]);

    expect(apiClient.post).toHaveBeenCalledWith('/jobs/job-1/runs');
    expect(apiClient.get).toHaveBeenCalledWith('/runs', { params: {} });
    expect(apiClient.get).toHaveBeenCalledWith('/jobs/job-1/runs', { params: {} });
  });

  test('createJob forwards prompt and pagination settings', async () => {
    const payload = {
      url: 'https://example.com/catalog',
      prompt: 'Find product prices',
      scrape_type: 'structured',
      max_pages: 25,
      follow_pagination: false,
    };
    apiClient.post.mockResolvedValue({ data: { id: 'job-1', ...payload } });

    await expect(api.createJob(payload)).resolves.toEqual({ id: 'job-1', ...payload });
    expect(apiClient.post).toHaveBeenCalledWith('/jobs', payload);
  });

  test('saas methods unwrap account and api key responses', async () => {
    apiClient.get
      .mockResolvedValueOnce({
        data: {
          plan: { plan: 'free', max_jobs: 5, max_runs_per_day: 20 },
          usage: { total_jobs: 1, total_runs: 2, total_exports: 3, runs_today: 1 },
        },
      })
      .mockResolvedValueOnce({
        data: {
          api_keys: [{ id: 'key-1', name: 'Primary', key_preview: 'ss_12...abcd' }],
          total: 1,
        },
      });
    apiClient.post.mockResolvedValue({
      data: { id: 'key-2', name: 'CLI', api_key: 'ss_secret', key: 'ss_secret' },
    });
    apiClient.delete.mockResolvedValue({ data: null });

    await expect(api.getAccountSummary()).resolves.toEqual({
      plan: { plan: 'free', max_jobs: 5, max_runs_per_day: 20 },
      usage: { total_jobs: 1, total_runs: 2, total_exports: 3, runs_today: 1 },
    });
    await expect(api.getApiKeys()).resolves.toEqual([
      { id: 'key-1', name: 'Primary', key_preview: 'ss_12...abcd' },
    ]);
    await expect(api.createApiKey({ name: 'CLI' })).resolves.toEqual({
      id: 'key-2',
      name: 'CLI',
      api_key: 'ss_secret',
      key: 'ss_secret',
    });
    await expect(api.deleteApiKey('key-2')).resolves.toBeNull();

    expect(apiClient.get).toHaveBeenCalledWith('/account/summary');
    expect(apiClient.get).toHaveBeenCalledWith('/api-keys', { params: {} });
    expect(apiClient.post).toHaveBeenCalledWith('/api-keys', { name: 'CLI' });
    expect(apiClient.delete).toHaveBeenCalledWith('/api-keys/key-2');
  });

  test('getHealth unwraps root health response', async () => {
    axios.get.mockResolvedValue({
      data: {
        status: 'ok',
        services: {
          database: 'ok',
          redis: 'ok',
          queue: 'ok',
        },
      },
    });

    await expect(api.getHealth()).resolves.toEqual({
      status: 'ok',
      services: {
        database: 'ok',
        redis: 'ok',
        queue: 'ok',
      },
    });
  });

  test('extractApiErrorMessage reads structured backend errors', () => {
    expect(
      extractApiErrorMessage({
        response: {
          data: {
            error: {
              message: 'Background worker dependencies are missing.',
            },
          },
        },
      })
    ).toBe('Background worker dependencies are missing.');
  });

  test('extractApiErrorMessage unwraps nested request validation details', () => {
    expect(
      extractApiErrorMessage({
        response: {
          data: {
            error: {
              code: 'request_validation_error',
              message: 'Request validation failed.',
              details: {
                errors: [
                  {
                    type: 'string_too_short',
                    loc: ['body', 'password'],
                    msg: 'String should have at least 8 characters',
                  },
                ],
              },
            },
          },
        },
      })
    ).toBe('Password: String should have at least 8 characters');
  });

  test('extractApiErrorMessage returns a helpful offline message for network errors', () => {
    expect(extractApiErrorMessage({ message: 'Network Error' })).toBe(
      'Cannot reach the API server at http://127.0.0.1:8000/api/v1. Start the backend and try again.'
    );
  });
});
