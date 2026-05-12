import React from 'react';

const BASE = 'rounded-2xl border border-white/10 bg-slate-950 p-4 shadow-sm';

const Card = ({ as: Component = 'section', className = '', children, ...props }) => (
  <Component className={`${BASE} ${className}`.trim()} {...props}>
    {children}
  </Component>
);

export default Card;
