jest.mock('axios', () => ({
  create: jest.fn(() => ({
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  })),
  get: jest.fn(),
}));

import axios from 'axios';
import api, { apiClient, clearSessionApiKey, extractApiErrorMessage, storeSessionApiKey } from './api';

describe('api service', () => {
  afterEach(() => {
    jest.clearAllMocks();
    clearSessionApiKey();
    window.localStorage.removeItem('access_token');
  });

  test('login sends x-www-form-urlencoded credentials', async () => {
    apiClient.post.mockResolvedValue({
      data: {
        access_token: 'token',
        token_type: 'bearer',
      },
    });

    await expect(api.login('demo@example.com', 'secret123')).resolves.toEqual({
      access_token: 'token',
      token_type: 'bearer',
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/auth/login',
      expect.any(URLSearchParams),
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      }
    );

    const [, formPayload] = apiClient.post.mock.calls[0];
    expect(formPayload.toString()).toContain('username=demo%40example.com');
    expect(formPayload.toString()).toContain('password=secret123');
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
    apiClient.get.mockResolvedValueOnce({
      data: {
        id: 'job-1',
        config: {
          max_records: 25,
          sources: ['internal', 'web'],
        },
      },
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

    expect(apiClient.post).toHaveBeenCalledWith(
      '/jobs/job-1/runs',
      expect.objectContaining({
        execution_contract: expect.objectContaining({
          execution_mode: 'multi_source',
          sources: ['internal', 'web'],
          limit: 25,
        }),
      })
    );
    expect(apiClient.get).toHaveBeenCalledWith('/runs', { params: {} });
    expect(apiClient.get).toHaveBeenCalledWith('/jobs/job-1/runs', { params: {} });
  });

  test('url-backed runs default to web-only execution when sources are not configured', async () => {
    apiClient.post.mockResolvedValue({
      data: { id: 'run-2', job_id: 'job-2', status: 'pending', progress: 0 },
    });
    apiClient.get.mockResolvedValueOnce({
      data: {
        id: 'job-2',
        url: 'https://example.com/patients',
        config: {
          max_records: 50,
        },
      },
    });

    await api.startJobRun('job-2');

    expect(apiClient.post).toHaveBeenCalledWith(
      '/jobs/job-2/runs',
      expect.objectContaining({
        execution_contract: expect.objectContaining({
          execution_mode: 'single_source',
          sources: ['web'],
          limit: 50,
        }),
      })
    );
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

  test('createJob retries without linked_page_workers when backend rejects unknown config key', async () => {
    const payload = {
      url: 'https://example.com/catalog',
      prompt: 'Find product prices',
      scrape_type: 'general',
      max_pages: 10,
      follow_pagination: true,
      config: {
        page_expansion_mode: 'same_domain',
        linked_page_limit: 20,
        linked_page_workers: 4,
        linked_page_keywords: ['price', 'product'],
      },
    };
    const schemaError = {
      response: {
        data: {
          detail: [
            {
              type: 'extra_forbidden',
              loc: ['body', 'config', 'linked_page_workers'],
              msg: 'Extra inputs are not permitted',
            },
          ],
        },
      },
    };

    apiClient.post
      .mockRejectedValueOnce(schemaError)
      .mockResolvedValueOnce({
        data: { id: 'job-compat-1', url: payload.url },
      });

    await expect(api.createJob(payload)).resolves.toEqual({ id: 'job-compat-1', url: payload.url });
    expect(apiClient.post).toHaveBeenNthCalledWith(1, '/jobs', payload);
    expect(apiClient.post).toHaveBeenNthCalledWith(
      2,
      '/jobs',
      expect.objectContaining({
        config: expect.not.objectContaining({ linked_page_workers: expect.anything() }),
      })
    );
  });

  test('deleteJobPermanently calls permanent deletion route', async () => {
    apiClient.delete.mockResolvedValue({
      data: { id: 'job-77', deleted: true },
    });

    await expect(api.deleteJobPermanently('job-77')).resolves.toEqual({
      id: 'job-77',
      deleted: true,
    });
    expect(apiClient.delete).toHaveBeenCalledWith('/jobs/job-77/permanent');
  });

  test('refineScrapeRequest sends assistant payload to backend', async () => {
    const payload = {
      url: 'https://example.com/catalog',
      draft_prompt: 'Need product details',
      user_message: 'Please make this clearer and complete',
      conversation: [],
    };
    apiClient.post.mockResolvedValue({
      data: {
        assistant_message: 'Refined successfully',
        refined_prompt: 'Extract title, price, stock from all listing pages.',
        recommended_scrape_type: 'structured',
        ready_to_apply: true,
        clarifying_questions: [],
        suggestions: [],
      },
    });

    await expect(api.refineScrapeRequest(payload)).resolves.toEqual(
      expect.objectContaining({
        assistant_message: 'Refined successfully',
        recommended_scrape_type: 'structured',
      })
    );
    expect(apiClient.post).toHaveBeenCalledWith('/assistant/request-refinement', payload);
  });

  test('runScrape sends canonical scrape payload to backend', async () => {
    const payload = {
      query: 'hospitals',
      location: 'Saudi Arabia',
      limit: 50,
      fields: ['name', 'contact', 'email'],
      request_id: 'req-1',
    };
    apiClient.post.mockResolvedValue({
      data: {
        request_id: 'req-1',
        status: 'completed',
        total: 1,
        data: [{ name: 'Demo Hospital' }],
        sources: [{ name: 'source-1', count: 1 }],
        errors: [],
        quality: {
          duplicates_removed: 0,
          coverage: 1,
          confidence: 0.9,
          missing_fields: {},
          normalized_fields: 3,
        },
      },
    });

    await expect(api.runScrape(payload)).resolves.toEqual(
      expect.objectContaining({
        request_id: 'req-1',
        status: 'completed',
      })
    );
    expect(apiClient.post).toHaveBeenCalledWith('/scrape', payload);
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

  test('storage cleanup methods use the user cleanup endpoints', async () => {
    apiClient.get.mockResolvedValueOnce({
      data: {
        history: { total_records: 4 },
        temp_files: { total_files: 7, estimated_freed_space_mb: 3.2 },
      },
    });
    apiClient.delete
      .mockResolvedValueOnce({ data: { status: 'success', deleted_history_records: 4 } })
      .mockResolvedValueOnce({ data: { status: 'success', deleted_temp_files: 7 } })
      .mockResolvedValueOnce({ data: { status: 'success', deleted_items_count: 11 } });

    await expect(api.getStorageCleanupSummary()).resolves.toEqual({
      history: { total_records: 4 },
      temp_files: { total_files: 7, estimated_freed_space_mb: 3.2 },
    });
    await expect(api.clearHistory()).resolves.toEqual({ status: 'success', deleted_history_records: 4 });
    await expect(api.clearTempFiles()).resolves.toEqual({ status: 'success', deleted_temp_files: 7 });
    await expect(api.clearAllUserData()).resolves.toEqual({ status: 'success', deleted_items_count: 11 });

    expect(apiClient.get).toHaveBeenCalledWith('/user/storage-summary');
    expect(apiClient.delete).toHaveBeenCalledWith('/user/history');
    expect(apiClient.delete).toHaveBeenCalledWith('/user/temp-files');
    expect(apiClient.delete).toHaveBeenCalledWith('/user/clear-all');
  });

  test('dashboard preference methods use user preference endpoints', async () => {
    apiClient.get.mockResolvedValueOnce({
      data: {
        preferences: {
          visibility: 'Internal Only',
          category_filter: 'All Workstreams',
          notifications: {
            budget_warnings: true,
            overdue_tasks: true,
            milestone_alerts: true,
            executive_digest: false,
          },
          plan_tags: ['Active'],
        },
      },
    });
    apiClient.put.mockResolvedValueOnce({
      data: {
        preferences: {
          visibility: 'Executive Review',
          category_filter: 'Design',
          notifications: {
            budget_warnings: false,
            overdue_tasks: true,
            milestone_alerts: true,
            executive_digest: false,
          },
          plan_tags: ['Priority Review'],
        },
      },
    });

    await expect(api.getDashboardPreferences()).resolves.toEqual(
      expect.objectContaining({
        preferences: expect.objectContaining({ visibility: 'Internal Only' }),
      })
    );
    await expect(
      api.updateDashboardPreferences({
        visibility: 'Executive Review',
        category_filter: 'Design',
        notifications: {
          budget_warnings: false,
          overdue_tasks: true,
          milestone_alerts: true,
          executive_digest: false,
        },
        plan_tags: ['Priority Review'],
      })
    ).resolves.toEqual(
      expect.objectContaining({
        preferences: expect.objectContaining({ visibility: 'Executive Review' }),
      })
    );

    expect(apiClient.get).toHaveBeenCalledWith('/user/preferences/dashboard');
    expect(apiClient.put).toHaveBeenCalledWith(
      '/user/preferences/dashboard',
      expect.objectContaining({ visibility: 'Executive Review' })
    );
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

  test('extractApiErrorMessage reads top-level backend message payloads', () => {
    expect(
      extractApiErrorMessage({
        response: {
          data: {
            error: 'service_unavailable',
            message: 'Rate limiting service unavailable',
          },
        },
      })
    ).toBe('Rate limiting service unavailable');
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
      'Cannot reach the API server at http://127.0.0.1:8001/api/v1. Start the backend and try again.'
    );
  });

  test('downloadExport returns blob with server-provided filename', async () => {
    apiClient.get.mockResolvedValue({
      data: new Blob(['binary']),
      headers: {
        'content-disposition': 'attachment; filename="export_123.pdf"',
      },
    });

    const result = await api.downloadExport('123');

    expect(apiClient.get).toHaveBeenCalledWith('/exports/123/download', { responseType: 'blob' });
    expect(result.filename).toBe('export_123.pdf');
    expect(result.blob).toBeInstanceOf(Blob);
  });

  test('downloadMultipleExports falls back to zip name when header missing', async () => {
    apiClient.post.mockResolvedValue({
      data: new Blob(['archive']),
      headers: {},
    });

    const result = await api.downloadMultipleExports(['e1', 'e2']);

    expect(apiClient.post).toHaveBeenCalledWith('/exports/download', ['e1', 'e2'], { responseType: 'blob' });
    expect(result.filename).toBe('bulk_export_2_files.zip');
    expect(result.blob).toBeInstanceOf(Blob);
  });

  test('session api key helpers persist and clear browser-scoped key', () => {
    storeSessionApiKey('ss_session_key_123');
    expect(window.sessionStorage.getItem('smart_scraper_api_key')).toBe('ss_session_key_123');
    expect(window.localStorage.getItem('smart_scraper_api_key')).toBeNull();

    clearSessionApiKey();
    expect(window.sessionStorage.getItem('smart_scraper_api_key')).toBeNull();
    expect(window.localStorage.getItem('smart_scraper_api_key')).toBeNull();
  });
});
