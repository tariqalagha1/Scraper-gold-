import React from 'react';
import Card from './Card';

const Section = ({ title, description, action = null, children, className = '', ...props }) => (
  <Card className={className} {...props}>
    {(title || description || action) && (
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          {title ? <h2 className="text-base font-semibold text-slate-100">{title}</h2> : null}
          {description ? <p className="mt-1 text-sm text-slate-400">{description}</p> : null}
        </div>
        {action}
      </div>
    )}
    <div className={title || description || action ? 'mt-4' : ''}>{children}</div>
  </Card>
);

export default Section;
