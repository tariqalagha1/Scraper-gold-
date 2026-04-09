import React from 'react';

const SectionHeader = ({ eyebrow, title, description, align = 'left' }) => (
  <div className={align === 'center' ? 'mx-auto max-w-4xl text-center' : 'max-w-4xl'}>
    {eyebrow && (
      <div className="mb-4 inline-flex rounded-full border border-accent/20 bg-accentSoft px-4 py-1.5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-accent">
          {eyebrow}
        </p>
      </div>
    )}
    <h2 className="text-4xl font-semibold tracking-tight text-textMain sm:text-5xl">
      {title}
    </h2>
    {description && (
      <p className="mt-5 text-base leading-8 text-textMuted sm:text-xl">
        {description}
      </p>
    )}
  </div>
);

export default SectionHeader;
