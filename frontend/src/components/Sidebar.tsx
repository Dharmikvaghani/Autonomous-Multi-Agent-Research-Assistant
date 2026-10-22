import React from 'react';
import {
  Bot,
  BrainCircuit,
  FileText,
  SlidersHorizontal,
  FolderKanban,
  Zap,
  ChevronRight,
  Activity,
  LogOut,
  User as UserIcon,
} from 'lucide-react';
import { User } from '../types';

interface SidebarProps {
  activeTab: 'research' | 'memory' | 'pdf' | 'settings';
  setActiveTab: (tab: 'research' | 'memory' | 'pdf' | 'settings') => void;
  workspaces: string[];
  currentWorkspace: string;
  setCurrentWorkspace: (ws: string) => void;
  backendOnline: boolean;
  isResearchRunning?: boolean;
  user?: User | null;
  onLogout?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  workspaces,
  currentWorkspace,
  setCurrentWorkspace,
  backendOnline,
  isResearchRunning = false,
  user,
  onLogout,
}) => {
  const navItems = [
    { id: 'research', label: 'Research Engine', icon: Bot, desc: 'Multi-agent pipeline', color: 'indigo' },
    { id: 'memory', label: 'Memory Bank', icon: BrainCircuit, desc: 'Vector knowledge', color: 'purple' },
    { id: 'pdf', label: 'PDF RAG Chat', icon: FileText, desc: 'Document Q&A', color: 'emerald' },
    { id: 'settings', label: 'Settings', icon: SlidersHorizontal, desc: 'Configuration', color: 'slate' },
  ] as const;

  return (
    <aside className="w-[260px] bg-[#0a0f1a] border-r border-slate-800/60 flex flex-col justify-between shrink-0 h-screen sticky top-0">
      <div>
        {/* Brand */}
        <div className="px-5 pt-6 pb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/30 animate-pulseGlow">
              <Zap className="w-5 h-5 text-white drop-shadow" />
            </div>
            <div>
              <h1 className="font-extrabold text-[17px] text-white tracking-tight leading-none">
                PRISM
              </h1>
              <p className="text-[10px] text-slate-500 font-medium mt-0.5 tracking-wide uppercase">Research Intelligence</p>
            </div>
          </div>
        </div>

        {/* Workspace */}
        <div className="px-4 pb-4">
          <div className="glass rounded-xl p-3">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block mb-2 flex items-center gap-1.5">
              <FolderKanban className="w-3 h-3 text-indigo-400" /> Workspace
            </label>
            <select
              value={currentWorkspace}
              onChange={(e) => setCurrentWorkspace(e.target.value)}
              className="w-full bg-[#0d1322] border border-slate-800/80 rounded-lg px-3 py-2 text-[11px] text-slate-200 focus:outline-none focus:border-indigo-500/50 font-medium cursor-pointer transition-colors"
            >
              {workspaces.map((ws) => (
                <option key={ws} value={ws}>
                  {ws === 'default' ? '🏠 Default' : `📁 ${ws}`}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Navigation */}
        <nav className="px-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`group w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs transition-all duration-200 ${
                  isActive
                    ? 'bg-gradient-to-r from-indigo-600/20 to-purple-600/10 text-white border border-indigo-500/25 shadow-sm shadow-indigo-500/10'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03] border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-1.5 rounded-lg transition-colors ${
                    isActive ? 'bg-indigo-500/20' : 'bg-slate-800/50 group-hover:bg-slate-800'
                  }`}>
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
                  </div>
                  <div className="text-left">
                    <span className={`block font-semibold text-[12px] ${isActive ? 'text-white' : ''}`}>{item.label}</span>
                    <span className={`block text-[9px] mt-0.5 ${isActive ? 'text-indigo-300/70' : 'text-slate-600'}`}>{item.desc}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  {item.id === 'research' && isResearchRunning && (
                    <span className="flex items-center gap-1 text-[9px] font-bold text-indigo-300 bg-indigo-500/20 border border-indigo-500/30 px-1.5 py-0.5 rounded-full animate-pulse">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-ping"></span>
                      Live
                    </span>
                  )}
                  <ChevronRight className={`w-3.5 h-3.5 transition-all ${
                    isActive ? 'text-indigo-400 opacity-100' : 'text-slate-700 opacity-0 group-hover:opacity-50'
                  }`} />
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Area: User Profile & System Status */}
      <div className="p-4 space-y-2.5">
        {user && (
          <div className="glass rounded-xl p-3 border border-slate-800/80">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center font-bold text-xs text-white shadow-md shadow-indigo-600/30 shrink-0">
                  {user.full_name ? user.full_name.charAt(0).toUpperCase() : user.username.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-white truncate leading-tight">
                    {user.full_name || user.username}
                  </p>
                  <p className="text-[10px] text-indigo-400 font-mono truncate">
                    @{user.username}
                  </p>
                </div>
              </div>
              {onLogout && (
                <button
                  type="button"
                  onClick={onLogout}
                  title="Sign Out"
                  className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-[10px]">
              <span className="text-slate-500 font-medium">Role</span>
              <span className="font-semibold text-slate-300 bg-slate-800/60 px-1.5 py-0.5 rounded">
                {user.role || 'Researcher'}
              </span>
            </div>
          </div>
        )}

        {/* System Status */}
        <div className="glass rounded-xl p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className={`w-3.5 h-3.5 ${backendOnline ? 'text-emerald-400' : 'text-rose-400'}`} />
              <span className="text-[11px] text-slate-400 font-medium">API Server</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`relative flex h-2 w-2 ${backendOnline ? '' : 'opacity-50'}`}>
                {backendOnline && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
                <span className={`relative inline-flex rounded-full h-2 w-2 ${backendOnline ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
              </span>
              <span className={`text-[10px] font-bold ${backendOnline ? 'text-emerald-400' : 'text-rose-400'}`}>
                {backendOnline ? 'Online' : 'Offline'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
