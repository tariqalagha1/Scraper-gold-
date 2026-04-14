import React from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import VisibilityRoundedIcon from '@mui/icons-material/VisibilityRounded';
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded';
import SettingsSuggestRoundedIcon from '@mui/icons-material/SettingsSuggestRounded';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import PsychologyRoundedIcon from '@mui/icons-material/PsychologyRounded';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import { useAuth } from '../context/AuthContext';

const navLinkClass = ({ isActive }) =>
  `rounded-xl border px-4 py-2 text-xs font-label uppercase tracking-[0.22em] transition ${
    isActive
      ? 'border-primary/30 bg-accentSoft text-primary shadow-glow'
      : 'border-transparent text-onSurfaceVariant hover:border-outlineVariant/20 hover:bg-white/5 hover:text-primary'
  }`;

const Navbar = () => {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="fixed top-0 z-50 w-full border-b border-outlineVariant/15 bg-background/75 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1440px] items-center justify-between px-6 py-4 lg:px-8">
        <Link to={isAuthenticated ? '/dashboard' : '/'} className="flex items-center gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary/30 bg-accentSoft text-primary shadow-glow">
            <VisibilityRoundedIcon fontSize="small" />
          </div>
          <div>
            <p className="font-headline text-sm font-bold uppercase tracking-[0.28em] text-primary">
              Smart Scraper
            </p>
            <p className="text-xs uppercase tracking-[0.18em] text-onSurfaceVariant">Web Data Workspace</p>
          </div>
        </Link>

        {isAuthenticated ? (
          <nav className="hidden items-center gap-2 rounded-2xl border border-outlineVariant/15 bg-surfaceContainer/70 px-2 py-2 shadow-panel md:flex">
            <NavLink to="/dashboard" className={navLinkClass}>
              <span className="inline-flex items-center gap-2">
                <PlayArrowRoundedIcon sx={{ fontSize: 18 }} />
                Dashboard
              </span>
            </NavLink>
            <NavLink to="/settings" className={navLinkClass}>
              <span className="inline-flex items-center gap-2">
                <SettingsSuggestRoundedIcon sx={{ fontSize: 18 }} />
                Settings
              </span>
            </NavLink>
            <NavLink to="/ai-integrations" className={navLinkClass}>
              <span className="inline-flex items-center gap-2">
                <PsychologyRoundedIcon sx={{ fontSize: 18 }} />
                AI Integrations
              </span>
            </NavLink>
            <NavLink to="/exports" className={navLinkClass}>
              <span className="inline-flex items-center gap-2">
                <DownloadRoundedIcon sx={{ fontSize: 18 }} />
                Exports
              </span>
            </NavLink>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-xl border border-outlineVariant/15 px-4 py-2 text-xs font-label uppercase tracking-[0.22em] text-onSurfaceVariant transition hover:border-primary/30 hover:bg-white/5 hover:text-onBackground"
            >
              <span className="inline-flex items-center gap-2">
                <LogoutRoundedIcon sx={{ fontSize: 18 }} />
                Logout
              </span>
            </button>
          </nav>
        ) : (
          <div className="flex items-center gap-3">
            <Link className="font-label text-xs uppercase tracking-[0.24em] text-onSurfaceVariant transition hover:text-primary" to="/login">
              Login
            </Link>
            <Link
              className="gel-shadow tonal-gradient rounded-xl px-5 py-3 font-label text-xs font-bold uppercase tracking-[0.24em] text-onPrimary transition hover:scale-[1.02]"
              to="/login"
            >
              Get Started
            </Link>
          </div>
        )}
      </div>
    </header>
  );
};

export default Navbar;
