import React from 'react';

const STATUS_STYLES = {
  idle: 'border-white/10 bg-surfaceAlt text-textMuted',
  success: 'border-success/30 bg-success/10 text-success',
  fail: 'border-danger/30 bg-danger/10 text-danger',
  running: 'border-accent/30 bg-accentSoft text-accent',
  accent: 'border-accent/30 bg-accentSoft text-accent',
  pending: 'border-warning/30 bg-warning/10 text-warning',
  skipped: 'border-white/10 bg-surfaceAlt text-textMuted',
  muted: 'border-white/10 bg-surfaceAlt text-textMuted',
};

const StatusBadge = ({ status = 'idle', children }) => {
  const normalized = String(status || 'idle').toLowerCase();
  const tone = STATUS_STYLES[normalized] || STATUS_STYLES.idle;

  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium capitalize ${tone} ${
        normalized === 'running' ? 'animate-pulse' : ''
      }`}
    >
      {children || normalized}
    </span>
  );
};

export default StatusBadge;
