import { Activity, LayoutDashboard, FilePlus2, Users, FileText, Settings, LogOut, ChevronLeft, ChevronRight, Wifi, WifiOff } from 'lucide-react';
import { useAuth } from '../store/AuthContext';
import type { DashboardTab } from '../types';

interface SidebarProps {
  activeTab:    DashboardTab;
  onTabChange:  (tab: DashboardTab) => void;
  isConnected:  boolean;
  collapsed:    boolean;
  onCollapse:   (v: boolean) => void;
}

const NAV_ITEMS: { id: DashboardTab; label: string; icon: React.ElementType }[] = [
  { id: 'telemetry',    label: 'Live Telemetry',  icon: LayoutDashboard },
  { id: 'new-analysis', label: 'New Analysis',    icon: FilePlus2 },
  { id: 'patients',     label: 'Patients',        icon: Users },
  { id: 'reports',      label: 'Reports',         icon: FileText },
  { id: 'settings',     label: 'Settings',        icon: Settings },
];

export default function Sidebar({
  activeTab,
  onTabChange,
  isConnected,
  collapsed,
  onCollapse,
}: SidebarProps) {
  const { user, logout } = useAuth();

  return (
    <aside
      className={`print-hidden relative flex flex-col h-full bg-cg-surface border-r border-cg-border
                  transition-all duration-300 ease-in-out
                  ${collapsed ? 'w-16' : 'w-60'}`}
    >
      {/* Toggle collapse */}
      <button
        id="btn-sidebar-collapse"
        onClick={() => onCollapse(!collapsed)}
        className="absolute -right-3 top-6 z-10 w-6 h-6 rounded-full border border-cg-border
                   bg-cg-surface flex items-center justify-center text-cg-muted hover:text-white
                   hover:border-indigo-500/50 transition-all duration-150"
        aria-label="Toggle sidebar"
      >
        {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>

      {/* Brand */}
      <div className={`flex items-center gap-3 p-4 mb-2 ${collapsed ? 'justify-center' : ''}`}>
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 
                        flex items-center justify-center glow-indigo">
          <Activity className="w-5 h-5 text-indigo-400" />
        </div>
        {!collapsed && (
          <div>
            <span className="block text-sm font-bold text-gradient-primary leading-tight">CardioGuard</span>
            <span className="block text-[10px] text-cg-muted leading-tight">AI Platform</span>
          </div>
        )}
      </div>

      {/* Kafka connection status pill */}
      <div className={`mx-3 mb-4 px-3 py-1.5 rounded-lg border text-xs flex items-center gap-2
                        ${isConnected
                          ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                          : 'bg-red-500/10 border-red-500/20 text-red-400'
                        }
                        ${collapsed ? 'justify-center px-2' : ''}`}>
        {isConnected
          ? <Wifi className="w-3.5 h-3.5 flex-shrink-0" />
          : <WifiOff className="w-3.5 h-3.5 flex-shrink-0" />
        }
        {!collapsed && (isConnected ? 'Kafka Live' : 'Disconnected')}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 space-y-1">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            id={`nav-${id}`}
            onClick={() => onTabChange(id)}
            className={`sidebar-item w-full ${activeTab === id ? 'active' : ''} ${collapsed ? 'justify-center' : ''}`}
            title={collapsed ? label : undefined}
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {!collapsed && <span>{label}</span>}
          </button>
        ))}
      </nav>

      {/* Footer: user + logout */}
      <div className={`p-3 border-t border-cg-border ${collapsed ? 'flex justify-center' : ''}`}>
        {!collapsed && (
          <div className="flex items-center gap-2 mb-3 px-1">
            <div className="w-8 h-8 rounded-full bg-indigo-600/30 flex items-center justify-center
                            text-xs font-bold text-indigo-300 flex-shrink-0">
              {user?.name.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-white truncate">{user?.name}</p>
              <p className="text-[10px] text-cg-muted truncate">{user?.role}</p>
            </div>
          </div>
        )}
        <button
          id="btn-logout"
          onClick={logout}
          className={`sidebar-item w-full text-red-400 hover:text-red-300 hover:bg-red-500/10
                      ${collapsed ? 'justify-center' : ''}`}
          title={collapsed ? 'Sign out' : undefined}
        >
          <LogOut className="w-4 h-4" />
          {!collapsed && 'Sign out'}
        </button>
      </div>
    </aside>
  );
}
