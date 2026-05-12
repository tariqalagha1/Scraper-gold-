import React from 'react';

const PageHeader = ({ title, description, actions = null }) => (
  <div className="flex flex-wrap items-start justify-between gap-3">
    <div>
      <h2 className="text-xl font-semibold text-slate-100">{title}</h2>
      {description ? <p className="mt-1 text-sm text-slate-400">{description}</p> : null}
    </div>
    {actions}
  </div>
);

export default PageHeader;
