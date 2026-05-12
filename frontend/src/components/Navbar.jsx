import React, { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import VisibilityRoundedIcon from '@mui/icons-material/VisibilityRounded';
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded';
import HistoryRoundedIcon from '@mui/icons-material/HistoryRounded';
import WorkspacesRoundedIcon from '@mui/icons-material/WorkspacesRounded';
import SettingsSuggestRoundedIcon from '@mui/icons-material/SettingsSuggestRounded';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded';
import PsychologyRoundedIcon from '@mui/icons-material/PsychologyRounded';
import PersonRoundedIcon from '@mui/icons-material/PersonRounded';
import KeyRoundedIcon from '@mui/icons-material/KeyRounded';
import MenuRoundedIcon from '@mui/icons-material/MenuRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import { useAuth } from '../context/AuthContext';
import { dashboardNavItems } from '../config/dashboardRegistry';

const navLinkClass = ({ isActive }) =>
  `rounded-xl border px-4 py-2 text-xs font-label uppercase tracking-[0.22em] transition ${
    isActive
      ? 'border-primary/30 bg-accentSoft text-primary shadow-glow'
      : 'border-transparent text-onSurfaceVariant hover:border-outlineVariant/20 hover:bg-white/5 hover:text-primary'
  }`;

const mobileNavLinkClass = ({ isActive }) =>
  `rounded-xl border px-4 py-2 text-xs font-label uppercase tracking-[0.18em] transition ${
    isActive
      ? 'border-primary/30 bg-accentSoft text-primary shadow-glow'
      : 'border-outlineVariant/15 text-onSurfaceVariant hover:border-outlineVariant/20 hover:bg-white/5 hover:text-primary'
  }`;

const navIcons = {
  dashboard: PlayArrowRoundedIcon,
  history: HistoryRoundedIcon,
  workspace: WorkspacesRoundedIcon,
  exports: DownloadRoundedIcon,
  demo: InsightsRoundedIcon,
  account: PersonRoundedIcon,
  'api-keys': KeyRoundedIcon,
  settings: SettingsSuggestRoundedIcon,
  'ai-integrations': PsychologyRoundedIcon,
  'system-keys': KeyRoundedIcon,
};

const Navbar = () => {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    setMobileMenuOpen(false);
    logout();
    navigate('/');
  };

  const handleNavClick = () => {
    setMobileMenuOpen(false);
  };

  const renderIcon = (key) => {
    const IconComponent = navIcons[key] || PlayArrowRoundedIcon;
    return <IconComponent sx={{ fontSize: 18 }} />;
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
          <>
            <nav className="hidden items-center gap-2 rounded-2xl border border-outlineVariant/15 bg-surfaceContainer/70 px-2 py-2 shadow-panel md:flex">
              {dashboardNavItems.map((item) => (
                <NavLink key={item.key} to={item.route} className={navLinkClass}>
                  <span className="inline-flex items-center gap-2">
                    {renderIcon(item.key)}
                    {item.label}
                  </span>
                </NavLink>
              ))}
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

            <div className="md:hidden">
              <button
                type="button"
                onClick={() => setMobileMenuOpen((previous) => !previous)}
                className="inline-flex items-center justify-center rounded-xl border border-outlineVariant/20 bg-surfaceContainer/80 px-3 py-2 text-onSurfaceVariant transition hover:border-primary/30 hover:text-primary"
                aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              >
                {mobileMenuOpen ? <CloseRoundedIcon sx={{ fontSize: 20 }} /> : <MenuRoundedIcon sx={{ fontSize: 20 }} />}
              </button>
            </div>
          </>
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
      {isAuthenticated && mobileMenuOpen && (
        <div className="border-t border-outlineVariant/15 bg-background/95 px-6 pb-4 pt-3 shadow-panel md:hidden">
          <nav className="flex flex-col gap-2">
            {dashboardNavItems.map((item) => (
              <NavLink key={item.key} to={item.route} className={mobileNavLinkClass} onClick={handleNavClick}>
                <span className="inline-flex items-center gap-2">
                  {renderIcon(item.key)}
                  {item.label}
                </span>
              </NavLink>
            ))}
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-xl border border-outlineVariant/15 px-4 py-2 text-xs font-label uppercase tracking-[0.18em] text-onSurfaceVariant transition hover:border-primary/30 hover:bg-white/5 hover:text-onBackground"
            >
              <span className="inline-flex items-center gap-2">
                <LogoutRoundedIcon sx={{ fontSize: 18 }} />
                Logout
              </span>
            </button>
          </nav>
        </div>
      )}
    </header>
  );
};

export default Navbar;
