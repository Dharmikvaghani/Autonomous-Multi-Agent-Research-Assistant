import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { ResearchConsole } from './components/ResearchConsole';
import { MemoryBank } from './components/MemoryBank';
import { PdfChat } from './components/PdfChat';
import { SettingsModal } from './components/SettingsModal';
import { LoginPage } from './components/LoginPage';
import { fetchSettings, fetchCurrentUser, logoutUser, getStoredToken } from './api';
import { User } from './types';
import { Loader2 } from 'lucide-react';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authChecking, setAuthChecking] = useState(true);

  const [activeTab, setActiveTab] = useState<'research' | 'memory' | 'pdf' | 'settings'>('research');
  const [workspaces, setWorkspaces] = useState<string[]>(['default']);
  const [currentWorkspace, setCurrentWorkspace] = useState<string>('default');
  const [backendOnline, setBackendOnline] = useState(false);
  const [isResearchRunning, setIsResearchRunning] = useState(false);

  // Check auth and load settings on mount
  useEffect(() => {
    let isMounted = true;

    // Hard fallback: never allow splash screen to hang for more than 2 seconds
    const fallbackTimer = setTimeout(() => {
      if (isMounted) {
        setAuthChecking(false);
      }
    }, 2000);

    const checkAuthAndSettings = async () => {
      try {
        const token = getStoredToken();
        if (token) {
          const user = await fetchCurrentUser();
          if (user && isMounted) {
            setCurrentUser(user);
          }
        }
      } catch (err) {
        console.warn('Initial auth check warning:', err);
      } finally {
        if (isMounted) {
          setAuthChecking(false);
          clearTimeout(fallbackTimer);
        }
      }

      // Fetch backend settings & workspaces
      fetchSettings()
        .then((s) => {
          if (isMounted) {
            setWorkspaces(s.available_workspaces || ['default']);
            setBackendOnline(true);
          }
        })
        .catch(() => {
          if (isMounted) setBackendOnline(false);
        });
    };

    checkAuthAndSettings();

    return () => {
      isMounted = false;
      clearTimeout(fallbackTimer);
    };
  }, []);

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
  };

  // Show minimal sleek loader during initial token check
  if (authChecking) {
    return (
      <div className="min-h-screen bg-[#060a13] flex items-center justify-center text-slate-100">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
          <p className="text-xs text-slate-500 tracking-wider font-semibold uppercase">Connecting to Prism AI...</p>
        </div>
      </div>
    );
  }

  // If not logged in, render the login page connected to the SQLite database
  if (!currentUser) {
    return <LoginPage onLoginSuccess={(user) => setCurrentUser(user)} />;
  }

  return (
    <div className="flex min-h-screen bg-[#060a13] text-slate-100 antialiased selection:bg-indigo-500/40 selection:text-white">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        workspaces={workspaces}
        currentWorkspace={currentWorkspace}
        setCurrentWorkspace={setCurrentWorkspace}
        backendOnline={backendOnline}
        isResearchRunning={isResearchRunning}
        user={currentUser}
        onLogout={handleLogout}
      />

      <main className="flex-1 overflow-y-auto max-h-screen">
        <div className="p-6 lg:p-10 max-w-[1400px] mx-auto">
          <div className={activeTab === 'research' ? 'block' : 'hidden'}>
            <ResearchConsole
              currentWorkspace={currentWorkspace}
              onExecutingChange={setIsResearchRunning}
            />
          </div>
          <div className={activeTab === 'memory' ? 'block' : 'hidden'}>
            <MemoryBank currentWorkspace={currentWorkspace} />
          </div>
          <div className={activeTab === 'pdf' ? 'block' : 'hidden'}>
            <PdfChat currentWorkspace={currentWorkspace} />
          </div>
          <div className={activeTab === 'settings' ? 'block' : 'hidden'}>
            <SettingsModal />
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;
