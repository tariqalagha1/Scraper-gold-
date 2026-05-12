import React from 'react';
import { NavLink } from 'react-router-dom';
import { Download, History, Home, KeyRound, PlugZap, Settings, UserRound, Workflow, X } from 'lucide-react';

const LINKS = [
  { key: 'dashboard', label: 'Dashboard', route: '/dashboard', icon: Home },
  { key: 'history', label: 'History', route: '/history', icon: History },
  { key: 'workspace', label: 'Workspace', route: '/workspace', icon: Workflow },
  { key: 'exports', label: 'Exports', route: '/exports', icon: Download },
  { key: 'api-keys', label: 'API Keys', route: '/api-keys', icon: KeyRound },
  { key: 'ai-integrations', label: 'Integrations', route: '/ai-integrations', icon: PlugZap },
  { key: 'account', label: 'Account', route: '/account', icon: UserRound },
  { key: 'settings', label: 'Settings', route: '/settings', icon: Settings },
];

const linkClasses = ({ isActive }) =>
  [
    'inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm transition',
    'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950',
    isActive
      ? 'border-slate-500 bg-slate-800 text-slate-100'
      : 'border-transparent text-slate-400 hover:border-white/10 hover:bg-slate-900 hover:text-slate-200',
  ].join(' ');

const SidebarLinks = ({ onNavigate = null }) => (
  <nav className="space-y-1">
    {LINKS.map((item) => {
      const Icon = item.icon;
      return (
        <NavLink key={item.key} to={item.route} className={linkClasses} onClick={onNavigate}>
          <Icon size={14} aria-hidden="true" />
          <span>{item.label}</span>
        </NavLink>
      );
    })}
  </nav>
);

const Sidebar = ({ mobile = false, open = false, onClose = null, id = 'dashboard-mobile-nav' }) => {
  if (mobile) {
    return (
      <div
        className={`fixed inset-0 z-50 lg:hidden ${open ? 'pointer-events-auto' : 'pointer-events-none'}`}
        aria-hidden={open ? 'false' : 'true'}
      >
        <button
          type="button"
          aria-label="Close navigation menu"
          onClick={onClose}
          className={`absolute inset-0 bg-black/60 transition-opacity ${open ? 'opacity-100' : 'opacity-0'}`}
        />

        <aside
          id={id}
          role="dialog"
          aria-label="Navigation menu"
          className={[
            'absolute left-0 top-0 h-full w-[280px] border-r border-white/10 bg-slate-950 p-4 shadow-xl transition-transform',
            open ? 'translate-x-0' : '-translate-x-full',
          ].join(' ')}
        >
          <div className="mb-4 flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-slate-500">Navigation</p>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close navigation"
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-slate-900 text-slate-300 transition hover:border-slate-500 hover:text-slate-100 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-950"
            >
              <X size={14} />
            </button>
          </div>

          <SidebarLinks onNavigate={onClose} />
        </aside>
      </div>
    );
  }

  return (
    <aside className="hidden rounded-2xl border border-white/10 bg-slate-900 p-3 lg:block">
      <p className="px-2 pb-3 text-xs uppercase tracking-wide text-slate-500">Navigation</p>
      <SidebarLinks />
    </aside>
  );
};

export default Sidebar;
