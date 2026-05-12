import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Bell, LogOut, Menu } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const TITLES = [
  {
    startsWith: '/dashboard',
    title: 'Dashboard',
    subtitle: 'Command center view with settings controls, feature status, and delivery timeline.',
  },
  { startsWith: '/history', title: 'History', subtitle: 'Review past runs and take action quickly.' },
  { startsWith: '/workspace', title: 'Run Workspace', subtitle: 'Watch pipeline progress and outputs in real time.' },
  { startsWith: '/exports', title: 'Exports', subtitle: 'Manage and download generated export files.' },
  { startsWith: '/api-keys', title: 'API Keys', subtitle: 'Create and manage secure API access keys.' },
  { startsWith: '/ai-integrations', title: 'Integrations', subtitle: 'Connect provider credentials for AI features.' },
  { startsWith: '/account', title: 'Account', subtitle: 'Review your account and plan usage.' },
  { startsWith: '/settings', title: 'Settings', subtitle: 'Adjust preferences and workspace defaults.' },
];

const resolveHeader = (pathname) => {
  const match = TITLES.find((item) => pathname.startsWith(item.startsWith));
  return match || { title: 'Workspace', subtitle: 'Manage scraping from a single dashboard.' };
};

const focusClass = 'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-900';

const Header = ({ onOpenNavigation = null, mobileNavOpen = false }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const header = resolveHeader(location.pathname);
  const userLabel = user?.email || 'Signed in user';

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="rounded-2xl border border-white/10 bg-slate-900 px-4 py-4 shadow-sm lg:px-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <button
            type="button"
            onClick={onOpenNavigation}
            aria-label="Open navigation menu"
            aria-expanded={mobileNavOpen}
            aria-controls="dashboard-mobile-nav"
            className={`inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-slate-950 text-slate-300 transition hover:border-slate-500 hover:text-slate-100 lg:hidden ${focusClass}`}
          >
            <Menu size={16} />
          </button>

          <div>
            <h1 className="text-xl font-semibold text-slate-100">{header.title}</h1>
            <p className="mt-1 text-sm text-slate-400">{header.subtitle}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className={`inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-slate-950 text-slate-300 transition hover:border-slate-500 hover:text-slate-100 ${focusClass}`}
            aria-label="Notifications"
          >
            <Bell size={16} />
          </button>

          <div className="hidden rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-right sm:block">
            <p className="text-[11px] uppercase tracking-wide text-slate-500">Signed in</p>
            <p className="text-sm text-slate-200">{userLabel}</p>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className={`inline-flex items-center gap-2 rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-300 transition hover:border-red-400/50 hover:text-red-200 ${focusClass}`}
          >
            <LogOut size={15} />
            Logout
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
