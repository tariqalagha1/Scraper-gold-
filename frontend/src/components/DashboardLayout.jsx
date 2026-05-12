import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';

const DashboardLayout = ({ children }) => {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!mobileNavOpen) return undefined;

    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        setMobileNavOpen(false);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [mobileNavOpen]);

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-6 lg:px-8">
      <Header onOpenNavigation={() => setMobileNavOpen(true)} mobileNavOpen={mobileNavOpen} />
      <Sidebar mobile open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />

      <div className="mt-4 lg:grid lg:grid-cols-[240px,1fr] lg:gap-6">
        <Sidebar />
        <main className="rounded-2xl border border-white/10 bg-slate-900 p-4 shadow-sm lg:p-6">{children}</main>
      </div>
    </div>
  );
};

export default DashboardLayout;
