import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { SurveillanceProvider, useSurveillance } from '../contexts/SurveillanceContext';
import OverviewPage from '../pages/OverviewPage';
import CamerasPage from '../pages/CamerasPage';
import AlertsPage from '../pages/AlertsPage';
import IntelligencePage from '../pages/IntelligencePage';
import AnalyticsPage from '../pages/AnalyticsPage';

type Page = 'overview' | 'cameras' | 'alerts' | 'intelligence' | 'analytics';

const navItems: { id: Page; label: string; icon: React.ReactNode }[] = [
  {
    id: 'overview',
    label: 'Overview',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
      </svg>
    ),
  },
  {
    id: 'cameras',
    label: 'Live Cameras',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    id: 'alerts',
    label: 'Alerts',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    ),
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
  {
    id: 'analytics',
    label: 'Analytics',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
];

const AppShell: React.FC = () => {
  const { user, logout } = useAuth();
  const { unreadAlerts, cameras, stats } = useSurveillance();
  const [activePage, setActivePage] = useState<Page>('overview');

  const activeCameras = cameras.filter((c) => c.is_active).length;

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 bg-gray-900 flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="px-4 py-5 border-b border-gray-800">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-blue-600 rounded-md flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </div>
            <span className="font-semibold text-white text-sm">ThirdEye</span>
          </div>
        </div>

        {/* System status strip */}
        {(activeCameras > 0 || (stats?.critical_alerts ?? 0) > 0) && (
          <div className="px-4 py-2 border-b border-gray-800 space-y-1">
            {activeCameras > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-green-400 rounded-full" />
                <span className="text-xs text-gray-400">{activeCameras} camera{activeCameras > 1 ? 's' : ''} active</span>
              </div>
            )}
            {(stats?.critical_alerts ?? 0) > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-red-400 rounded-full" />
                <span className="text-xs text-red-400">{stats!.critical_alerts} critical</span>
              </div>
            )}
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActivePage(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
                {item.id === 'alerts' && unreadAlerts > 0 && (
                  <span className="ml-auto inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold bg-red-500 text-white rounded-full">
                    {unreadAlerts > 9 ? '9+' : unreadAlerts}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="px-4 py-4 border-t border-gray-800">
          {user && (
            <p className="text-xs text-gray-500 truncate mb-2" title={user.email}>{user.email}</p>
          )}
          <button
            onClick={logout}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        {activePage === 'overview' && <OverviewPage onNavigate={(p) => setActivePage(p as Page)} />}
        {activePage === 'cameras' && <CamerasPage />}
        {activePage === 'alerts' && <AlertsPage />}
        {activePage === 'intelligence' && <IntelligencePage />}
        {activePage === 'analytics' && <AnalyticsPage />}
      </div>
    </div>
  );
};

function Dashboard() {
  return (
    <SurveillanceProvider>
      <AppShell />
    </SurveillanceProvider>
  );
}

export default Dashboard;
