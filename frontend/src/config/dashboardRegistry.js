import React from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import AccountPage from '../pages/AccountPage';
import IntegrationsPage from '../pages/AiIntegrationsPage';
import ApiKeysPage from '../pages/ApiKeysPage';
import DashboardPage from '../pages/DashboardPage';
import HistoryPage from '../pages/HistoryPage';
import SettingsPage from '../pages/SettingsPage';
import SystemKeysPage from '../pages/SystemKeysPage';
import DashboardLayout from '../components/DashboardLayout';
import ExportManagementPanel from '../components/ExportManagementPanel';
import ExportStatusView from '../components/ExportStatusView';
import JobWorkspacePanel from '../components/JobWorkspacePanel';
import StakeholderDemoPanel from '../components/StakeholderDemoPanel';

const DashboardRoute = () => (
  <DashboardLayout>
    <DashboardPage />
  </DashboardLayout>
);

const HistoryRoute = () => (
  <DashboardLayout>
    <HistoryPage />
  </DashboardLayout>
);

const WorkspaceRoute = () => {
  const { jobId: routeJobId } = useParams();
  const [searchParams] = useSearchParams();
  const queryJobId = searchParams.get('jobId') || '';

  return (
    <DashboardLayout>
      <JobWorkspacePanel jobId={routeJobId || queryJobId} />
    </DashboardLayout>
  );
};

const ExportsRoute = () => (
  <DashboardLayout>
    <ExportManagementPanel />
  </DashboardLayout>
);

const ExportStatusRoute = () => (
  <DashboardLayout>
    <ExportStatusView />
  </DashboardLayout>
);

const DemoRoute = () => (
  <DashboardLayout>
    <StakeholderDemoPanel />
  </DashboardLayout>
);

const AccountRoute = () => (
  <DashboardLayout>
    <AccountPage />
  </DashboardLayout>
);

const ApiKeysRoute = () => (
  <DashboardLayout>
    <ApiKeysPage />
  </DashboardLayout>
);

const SettingsRoute = () => (
  <DashboardLayout>
    <SettingsPage />
  </DashboardLayout>
);

const IntegrationsRoute = () => (
  <DashboardLayout>
    <IntegrationsPage />
  </DashboardLayout>
);

const SystemKeysRoute = () => (
  <DashboardLayout>
    <SystemKeysPage />
  </DashboardLayout>
);

export const dashboardRegistry = [
  {
    key: 'dashboard',
    label: 'Dashboard',
    route: '/dashboard',
    component: DashboardRoute,
    protected: true,
    showInNav: true,
  },
  {
    key: 'history',
    label: 'History',
    route: '/history',
    component: HistoryRoute,
    protected: true,
    showInNav: true,
  },
  {
    key: 'workspace',
    label: 'Workspace',
    route: '/workspace',
    component: WorkspaceRoute,
    protected: true,
    showInNav: true,
  },
  {
    key: 'workspace-job',
    label: 'Workspace',
    route: '/workspace/:jobId',
    component: WorkspaceRoute,
    protected: true,
    showInNav: false,
  },
  {
    key: 'exports',
    label: 'Exports',
    route: '/exports',
    component: ExportsRoute,
    protected: true,
    showInNav: true,
  },
  {
    key: 'export-status',
    label: 'Export Status',
    route: '/exports/status',
    component: ExportStatusRoute,
    protected: true,
    showInNav: false,
  },
  {
    key: 'demo',
    label: 'Demo',
    route: '/demo',
    component: DemoRoute,
    protected: true,
    showInNav: true,
  },
  {
    key: 'account',
    label: 'Account',
    route: '/account',
    component: AccountRoute,
    protected: true,
    showInNav: true,
  },
  {
    key: 'api-keys',
    label: 'API Keys',
    route: '/api-keys',
    component: ApiKeysRoute,
    protected: true,
    showInNav: true,
  },
  {
    key: 'settings',
    label: 'Settings',
    route: '/settings',
    component: SettingsRoute,
    protected: true,
    showInNav: true,
  },
  {
    key: 'ai-integrations',
    label: 'Integrations',
    route: '/ai-integrations',
    component: IntegrationsRoute,
    protected: true,
    showInNav: true,
  },
  {
    key: 'system-keys',
    label: 'System Keys',
    route: '/system-keys',
    component: SystemKeysRoute,
    protected: true,
    showInNav: true,
  },
];

export const dashboardNavItems = dashboardRegistry.filter((item) => item.showInNav);
