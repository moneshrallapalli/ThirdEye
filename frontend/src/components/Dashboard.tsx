import React, { useState, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { SurveillanceProvider, useSurveillance } from '../contexts/SurveillanceContext';
import { AlertSeverity } from '../types';
import OverviewPage from '../pages/OverviewPage';
import CamerasPage from '../pages/CamerasPage';
import TasksPage from '../pages/TasksPage';
import AlertsPage from '../pages/AlertsPage';
import IntelligencePage from '../pages/IntelligencePage';
import AnalyticsPage from '../pages/AnalyticsPage';

type Page = 'overview' | 'cameras' | 'tasks' | 'alerts' | 'intelligence' | 'analytics';

const navItems: { id: Page; label: string; icon: React.ReactNode }[] = [
  {
    id: 'overview',
    label: 'Overview',
    icon: (
      <svg className="w-[15px] h-[15px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
      </svg>
    ),
  },
  {
    id: 'cameras',
    label: 'Live Cameras',
    icon: (
      <svg className="w-[15px] h-[15px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    id: 'tasks',
    label: 'Monitoring',
    icon: (
      <svg className="w-[15px] h-[15px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
  },
  {
    id: 'alerts',
    label: 'Alerts',
    icon: (
      <svg className="w-[15px] h-[15px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    ),
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    icon: (
      <svg className="w-[15px] h-[15px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
  {
    id: 'analytics',
    label: 'Analytics',
    icon: (
      <svg className="w-[15px] h-[15px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
];

const AppShell: React.FC = () => {
  const { user, logout } = useAuth();
  const { theme, toggle: toggleTheme } = useTheme();
  const { unreadAlerts, cameras, alerts } = useSurveillance();
  const [activePage, setActivePage] = useState<Page>('overview');
  const [alertFilter, setAlertFilter] = useState<string | undefined>(undefined);

  const handleNavigate = (target: string) => {
    const [page, filter] = target.split(':');
    setActivePage(page as Page);
    setAlertFilter(filter);
  };

  const activeCameras = cameras.filter((c) => c.is_active).length;

  // Use the exact same source + filter as the Alerts page so the sidebar's
  // "N critical" badge always matches the page's "Critical (N)" tab. We
  // previously read `stats.critical_alerts` from /api/stats/summary, which
  // counted (a) every severity=CRITICAL row (including legacy generic ones)
  // over (b) only the last 24h — two mismatches versus the Alerts page.
  const userTriggeredAlerts = alerts.filter(
    (a) => !!(a.user_query || a.alert_type === 'trigger_match')
  );
  const criticalCount = userTriggeredAlerts.filter(
    (a) => a.severity === AlertSeverity.CRITICAL
  ).length;

  const [isMouseInSidebar, setIsMouseInSidebar] = useState(false);
  const [pupilOffset, setPupilOffset] = useState({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);

  const handleSidebarMouseMove = (e: React.MouseEvent) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const eyeCenterX = rect.left + rect.width * (55 / 110);
    const eyeCenterY = rect.top + rect.height * (45 / 82);
    const dx = e.clientX - eyeCenterX;
    const dy = e.clientY - eyeCenterY;
    // Convert screen pixels to SVG user units
    const svgX = dx * (110 / rect.width);
    const svgY = dy * (82 / rect.height);
    // Clamp to max 7 SVG units so pupil stays inside iris
    const maxR = 7;
    const dist = Math.sqrt(svgX * svgX + svgY * svgY);
    const scale = dist > maxR ? maxR / dist : 1;
    setPupilOffset({ x: svgX * scale, y: svgY * scale });
  };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg-page)' }}>
      {/* Sidebar */}
      <aside
        className="w-52 flex flex-col flex-shrink-0"
        style={{ background: 'var(--bg-sidebar)', borderRight: '1px solid var(--border)' }}
        onMouseEnter={() => setIsMouseInSidebar(true)}
        onMouseLeave={() => {
          setPupilOffset({ x: 0, y: 0 });
          setTimeout(() => setIsMouseInSidebar(false), 150);
        }}
        onMouseMove={handleSidebarMouseMove}
      >
        {/* Logo */}
        <div className="px-4 pt-6 pb-5 flex flex-col items-center" style={{ borderBottom: '1px solid var(--border)' }}>
          {/* Animated eye logo */}
          <svg ref={svgRef} width="132" height="98" viewBox="0 0 110 82" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ color: 'var(--text-primary)' }}>
            <defs>
              <clipPath id="eye-lid-clip">
                <path d="M3 45 C24 16 86 16 107 45 C86 74 24 74 3 45 Z"/>
              </clipPath>
            </defs>

            {/* Eyebrow — raises on blink */}
            <path
              d="M20 10 C42 2 68 2 90 10"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              fill="none"
              opacity="0.5"
              className="eye-brow"
            />

            {/* Eye corner accents */}
            <line x1="3" y1="45" x2="0" y2="45" stroke="currentColor" strokeWidth="1.2" opacity="0.25"/>
            <line x1="107" y1="45" x2="110" y2="45" stroke="currentColor" strokeWidth="1.2" opacity="0.25"/>

            {/* All eye contents — clipped to eye shape */}
            <g clipPath="url(#eye-lid-clip)">
              {/* Eye fill */}
              <path d="M3 45 C24 16 86 16 107 45 C86 74 24 74 3 45 Z" fill="currentColor" fillOpacity="0.04"/>

              {/* Circuit board traces — converge from sclera edges toward iris */}

              {/* Left sclera */}
              <path d="M 4 45 H 35"              className="ct-trace ct-a"/>
              <path d="M 7 50 H 21 V 45 H 35"    className="ct-trace ct-b"/>
              <path d="M 11 40 H 36"             className="ct-trace ct-c"/>
              <path d="M 20 32 V 40 H 37"        className="ct-trace ct-d"/>

              {/* Right sclera */}
              <path d="M 106 45 H 75"            className="ct-trace ct-a"/>
              <path d="M 103 50 H 89 V 45 H 75"  className="ct-trace ct-b"/>
              <path d="M 99 40 H 74"             className="ct-trace ct-c"/>
              <path d="M 90 32 V 40 H 73"        className="ct-trace ct-d"/>

              {/* Top sclera */}
              <path d="M 48 18 V 27 H 52"        className="ct-trace ct-c"/>
              <path d="M 62 18 V 27 H 58"        className="ct-trace ct-d"/>

              {/* Bottom sclera */}
              <path d="M 48 72 V 63 H 52"        className="ct-trace ct-d"/>
              <path d="M 62 72 V 63 H 58"        className="ct-trace ct-c"/>

              {/* Junction nodes */}
              <circle cx="21" cy="45" r="1.4" className="ct-dot ct-dot-b"/>
              <circle cx="89" cy="45" r="1.4" className="ct-dot ct-dot-b"/>
              <circle cx="20" cy="40" r="1.1" className="ct-dot ct-dot-d"/>
              <circle cx="90" cy="40" r="1.1" className="ct-dot ct-dot-d"/>
              <circle cx="52" cy="27" r="1.1" className="ct-dot ct-dot-c"/>
              <circle cx="58" cy="27" r="1.1" className="ct-dot ct-dot-d"/>
              <circle cx="52" cy="63" r="1.1" className="ct-dot ct-dot-d"/>
              <circle cx="58" cy="63" r="1.1" className="ct-dot ct-dot-c"/>

              {/* Iris outer */}
              <circle cx="55" cy="45" r="20" stroke="currentColor" strokeWidth="1" fill="currentColor" fillOpacity="0.05" opacity="0.5"/>
              {/* Iris inner detail */}
              <circle cx="55" cy="45" r="13" stroke="currentColor" strokeWidth="0.7" fill="none" opacity="0.2"/>

              {/* Orbiting scanner dot */}
              <g className="iris-orbit">
                <circle cx="55" cy="25" r="1.1" fill="currentColor" opacity="0.12" transform="rotate(-24 55 45)"/>
                <circle cx="55" cy="25" r="1.4" fill="currentColor" opacity="0.22" transform="rotate(-15 55 45)"/>
                <circle cx="55" cy="25" r="1.7" fill="currentColor" opacity="0.38" transform="rotate(-8 55 45)"/>
                <line x1="55" y1="45" x2="55" y2="25" stroke="currentColor" strokeWidth="0.8" opacity="0.12"/>
                <circle cx="55" cy="25" r="2.6" fill="currentColor" opacity="0.9"/>
              </g>

              {/* Pupil + highlight — moves like human eye, tracks mouse when in sidebar */}
              <g
                className={isMouseInSidebar ? undefined : 'eye-pupil-group'}
                style={isMouseInSidebar ? {
                  animation: 'none',
                  transform: `translate(${pupilOffset.x}px, ${pupilOffset.y}px)`,
                  transition: 'transform 0.08s ease-out',
                } : undefined}
              >
                <circle cx="55" cy="45" r="8" fill="currentColor"/>
                <circle cx="58.5" cy="41.5" r="2.4" fill="white" opacity="0.85"/>
              </g>

              {/* Iris ping */}
              <circle cx="55" cy="45" r="8" fill="none" stroke="currentColor" strokeWidth="1.2" className="iris-ping"/>

              {/* Upper eyelid — descends from top on blink */}
              <rect x="-5" y="-5" width="120" height="55" style={{ fill: 'var(--eyelid-fill)' }} className="eyelid-top"/>
              {/* Lower eyelid — rises from bottom on blink */}
              <rect x="-5" y="45" width="120" height="42" style={{ fill: 'var(--eyelid-fill)' }} className="eyelid-bottom"/>
            </g>

            {/* Eye outline — always on top of eyelids */}
            <path
              d="M3 45 C24 16 86 16 107 45 C86 74 24 74 3 45 Z"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinejoin="round"
            />

            {/* Lower lid crease */}
            <path
              d="M18 54 C38 63 72 63 92 54"
              stroke="currentColor"
              strokeWidth="0.8"
              fill="none"
              opacity="0.13"
            />
          </svg>

          <span className="font-display font-bold text-3xl mt-1" style={{ color: 'var(--text-primary)', letterSpacing: '-0.04em' }}>
            ThirdEye
          </span>
        </div>

        {/* System status */}
        {(activeCameras > 0 || criticalCount > 0) && (
          <div className="px-5 py-2.5 space-y-1" style={{ borderBottom: '1px solid var(--border)' }}>
            {activeCameras > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: 'var(--status-live)' }} />
                <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                  {activeCameras} active
                </span>
              </div>
            )}
            {criticalCount > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: 'var(--sev-critical-bar)' }} />
                <span className="text-[11px]" style={{ color: 'var(--sev-critical-text)' }}>
                  {criticalCount} critical
                </span>
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
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium transition-all"
                style={{
                  color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                  background: isActive ? 'var(--border)' : 'transparent',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)';
                    (e.currentTarget as HTMLElement).style.background = 'var(--bg-surface-hover)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)';
                    (e.currentTarget as HTMLElement).style.background = 'transparent';
                  }
                }}
              >
                {item.icon}
                <span>{item.label}</span>
                {item.id === 'alerts' && unreadAlerts > 0 && (
                  <span
                    className="ml-auto text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                    style={{ background: 'var(--btn-primary-bg)', color: 'var(--btn-primary-text)' }}
                  >
                    {unreadAlerts > 9 ? '9+' : unreadAlerts}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="px-5 py-4" style={{ borderTop: '1px solid var(--border)' }}>
          {user && (
            <p className="text-[11px] truncate mb-2" style={{ color: 'var(--text-faint)' }} title={user.email}>
              {user.email}
            </p>
          )}
          <div className="flex items-center justify-between">
            <button
              onClick={logout}
              className="text-[11px] transition-colors"
              style={{ color: 'var(--text-muted)' }}
              onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--text-primary)')}
              onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--text-muted)')}
            >
              Sign out
            </button>
            <button
              onClick={toggleTheme}
              className="w-7 h-7 rounded-md flex items-center justify-center transition-colors"
              style={{ color: 'var(--text-muted)' }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)';
                (e.currentTarget as HTMLElement).style.background = 'var(--bg-surface-hover)';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)';
                (e.currentTarget as HTMLElement).style.background = 'transparent';
              }}
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? (
                <svg className="w-[15px] h-[15px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
                </svg>
              ) : (
                <svg className="w-[15px] h-[15px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
                </svg>
              )}
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        {activePage === 'overview'     && <OverviewPage onNavigate={handleNavigate} />}
        {activePage === 'cameras'      && <CamerasPage onNavigateToTasks={() => setActivePage('tasks')} />}
        {activePage === 'tasks'        && <TasksPage />}
        {activePage === 'alerts'       && <AlertsPage initialFilter={alertFilter} />}
        {activePage === 'intelligence' && <IntelligencePage />}
        {activePage === 'analytics'    && <AnalyticsPage />}
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
