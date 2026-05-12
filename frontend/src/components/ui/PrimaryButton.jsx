import React from 'react';

const PrimaryButton = ({ className = '', fullWidthMobile = true, children, ...props }) => (
  <button
    className={[
      'rounded-xl border border-white/10 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-100 transition',
      'hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60',
      'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950',
      fullWidthMobile ? 'w-full sm:w-auto' : '',
      className,
    ]
      .filter(Boolean)
      .join(' ')}
    {...props}
  >
    {children}
  </button>
);

export default PrimaryButton;
