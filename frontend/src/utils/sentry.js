import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';

const initializeSentry = () => {
  const dsn = process.env.REACT_APP_SENTRY_DSN;

  if (!dsn) {
    console.warn('Sentry DSN not configured');
    return;
  }

  Sentry.init({
    dsn,
    integrations: [new BrowserTracing()],
    tracesSampleRate: 1.0,
    environment: process.env.NODE_ENV || 'development',
    beforeSend(event) {
      // Don't send events in development unless explicitly configured
      if (process.env.NODE_ENV === 'development' && !process.env.REACT_APP_SENTRY_DEV) {
        return null;
      }
      return event;
    },
  });
};

export default initializeSentry;