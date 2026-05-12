export const UX_EVENT_CHANNEL = 'brainit:ux_event';

export const UX_EVENTS = {
  ONBOARDING_MODAL_SHOWN: 'onboarding_modal_shown',
  SAMPLE_SELECTED: 'sample_selected',
  REQUEST_REFINED: 'request_refined',
  STRUCTURED_PREVIEW_ACCEPTED: 'structured_preview_accepted',
  TASK_RUN_STARTED: 'task_run_started',
  TASK_COMPLETED_SUCCESSFULLY: 'task_completed_successfully',
};

export const trackUxEvent = (eventName, payload = {}) => {
  const detail = {
    event: String(eventName || '').trim(),
    payload: payload && typeof payload === 'object' ? payload : {},
    timestamp: new Date().toISOString(),
  };

  if (!detail.event) {
    return;
  }

  if (typeof window !== 'undefined') {
    try {
      window.dispatchEvent(new CustomEvent(UX_EVENT_CHANNEL, { detail }));
    } catch {
      // Ignore browser event dispatch errors.
    }
  }

  if (process.env.NODE_ENV !== 'production' && process.env.NODE_ENV !== 'test') {
    // Lightweight developer hook until a full analytics sink is wired.
    // eslint-disable-next-line no-console
    console.info('[brainit:ux]', detail);
  }
};
