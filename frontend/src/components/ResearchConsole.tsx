import React, { useState, useEffect, useRef } from 'react';
import {
  Play,
  Square,
  Terminal,
  Search,
  Sparkles,
  Globe,
  Repeat,
  SlidersHorizontal,
  Loader2,
  ArrowRight,
  Cpu,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { startResearch, getResearchStatus } from '../api';
import { ResearchTaskState } from '../types';
import { WorkflowVisualizer } from './WorkflowVisualizer';
import { ReportViewer } from './ReportViewer';

interface ResearchConsoleProps {
  currentWorkspace: string;
  onExecutingChange?: (executing: boolean) => void;
}

export const ResearchConsole: React.FC<ResearchConsoleProps> = ({ currentWorkspace, onExecutingChange }) => {
  const [topic, setTopic] = useState('');
  const [targetWordCount, setTargetWordCount] = useState(2000);
  const [selfCorrectionRounds, setSelfCorrectionRounds] = useState(1);
  const [searchProvider, setSearchProvider] = useState('tavily');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showTerminal, setShowTerminal] = useState(false);

  const [taskState, setTaskState] = useState<ResearchTaskState | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const logEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Notify parent of execution state
  useEffect(() => {
    onExecutingChange?.(isExecuting);
  }, [isExecuting, onExecutingChange]);

  // Auto-scroll log viewer
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [taskState?.logs]);

  // Clean up EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const pollIntervalRef = useRef<any>(null);

  const pollStatus = (taskId: string) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    let errorCount = 0;
    pollIntervalRef.current = setInterval(async () => {
      try {
        const statusData = await getResearchStatus(taskId);
        errorCount = 0;
        setTaskState({
          task_id: statusData.task_id,
          status: statusData.status,
          topic: statusData.topic,
          logs: statusData.logs || [],
          steps: statusData.tasks || {},
          result: {
            final_report: statusData.final_report,
            summary: statusData.summary,
            critique: statusData.critique,
            pipeline_status: statusData.status,
            tasks: statusData.tasks || {}
          },
          duration: statusData.duration
        });

        if (statusData.status === 'COMPLETED' || statusData.status === 'FAILED') {
          setIsExecuting(false);
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      } catch {
        errorCount += 1;
        if (errorCount > 10) {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          setIsExecuting(false);
        }
      }
    }, 2000);
  };

  // Reusable SSE connection helper
  const connectSSE = (taskId: string, fallbackTopic: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const sseUrl = `/api/research/stream/${taskId}`;
    const es = new EventSource(sseUrl);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'init' || data.type === 'step_update') {
          setTaskState((prev) => ({
            task_id: data.task_id || prev?.task_id || taskId,
            status: data.status || prev?.status || 'RUNNING',
            topic: data.topic || prev?.topic || fallbackTopic,
            logs: data.logs ? [...data.logs] : (prev?.logs || []),
            steps: data.steps ? { ...data.steps } : (prev?.steps || {}),
            result: data.result || prev?.result,
          }));
        } else if (data.type === 'log') {
          setTaskState((prev) => prev ? ({
            ...prev,
            status: data.status || prev.status,
            logs: [...prev.logs, data.message],
          }) : null);
        } else if (data.type === 'complete') {
          setTaskState((prev) => prev ? ({
            ...prev,
            status: data.status || 'COMPLETED',
            result: data.result,
          }) : null);
          setIsExecuting(false);
          es.close();
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        } else if (data.type === 'error') {
          setErrorMsg(data.error || 'Research pipeline failed');
          setIsExecuting(false);
          es.close();
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };

    es.onerror = () => {
      es.close();
      pollStatus(taskId);
    };
  };

  // Restore active or previous task on mount (e.g. page refresh / tab switch)
  useEffect(() => {
    const savedTaskId = localStorage.getItem('prism_active_task_id');
    if (savedTaskId && !taskState) {
      getResearchStatus(savedTaskId)
        .then((statusData) => {
          if (statusData && statusData.task_id) {
            setTopic(statusData.topic || '');
            setTaskState({
              task_id: statusData.task_id,
              status: statusData.status,
              topic: statusData.topic,
              logs: statusData.logs || [],
              steps: statusData.tasks || {},
              result: {
                final_report: statusData.final_report,
                summary: statusData.summary,
                critique: statusData.critique,
                pipeline_status: statusData.status,
                tasks: statusData.tasks || {}
              },
              duration: statusData.duration
            });

            if (statusData.status === 'RUNNING' || statusData.status === 'PENDING') {
              setIsExecuting(true);
              connectSSE(statusData.task_id, statusData.topic);
            }
          }
        })
        .catch((err) => {
          console.warn('Could not restore past task:', err);
        });
    }
  }, []);

  const handleStartResearch = async () => {
    if (!topic.trim()) return;

    setErrorMsg(null);
    setIsExecuting(true);
    setTaskState(null);

    try {
      const taskInit = await startResearch(
        topic.trim(),
        targetWordCount,
        selfCorrectionRounds,
        searchProvider,
        currentWorkspace
      );

      localStorage.setItem('prism_active_task_id', taskInit.task_id);

      setTaskState({
        task_id: taskInit.task_id,
        status: 'RUNNING',
        topic: topic.trim(),
        logs: [`⚡ Connected to research pipeline — Task ${taskInit.task_id}`],
        steps: {},
      });

      connectSSE(taskInit.task_id, topic.trim());
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start research task');
      setIsExecuting(false);
    }
  };

  const handleStopResearch = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    setIsExecuting(false);
    localStorage.removeItem('prism_active_task_id');
    setTaskState((prev) => prev ? ({
      ...prev,
      status: 'FAILED',
      logs: [...prev.logs, '⛔ Execution halted by user.'],
    }) : null);
  };

  return (
    <div className="space-y-6 animate-fadeInUp">
      {/* Hero Header */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-800/60">
        {/* Animated gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-950/60 via-[#0a0f1a] to-purple-950/40"></div>
        <div className="absolute top-0 right-0 w-[500px] h-[400px] bg-indigo-600/8 rounded-full blur-[100px] pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 w-[400px] h-[300px] bg-purple-600/8 rounded-full blur-[80px] pointer-events-none"></div>

        <div className="relative z-10 p-7">
          {/* Top badge row */}
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20">
                <Cpu className="w-3 h-3 text-indigo-400" />
                <span className="text-[10px] font-bold uppercase text-indigo-400 tracking-wider">Multi-Agent Engine</span>
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                <Sparkles className="w-3 h-3 text-emerald-400" />
                <span className="text-[10px] font-bold uppercase text-emerald-400 tracking-wider">9 AI Agents</span>
              </div>
            </div>
          </div>

          {/* Title */}
          <h2 className="text-3xl font-extrabold text-white tracking-tight mb-1">
            Deep Research Console
          </h2>
          <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
            Enter any research topic. Autonomous agents will plan, search, draft, critique, and synthesize a comprehensive research report.
          </p>

          {/* Search Input */}
          <div className="mt-6 relative group">
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-indigo-500/20 via-purple-500/20 to-indigo-500/20 blur-sm opacity-0 group-focus-within:opacity-100 transition-opacity duration-300"></div>
            <div className="relative flex items-center">
              <Search className="w-5 h-5 text-slate-500 absolute left-4 pointer-events-none" />
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isExecuting && handleStartResearch()}
                placeholder="e.g., Quantum Computing in Financial Risk Modeling..."
                className="w-full bg-[#0d1322]/90 border border-slate-700/60 rounded-2xl pl-12 pr-44 py-4 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 transition-colors"
              />
              <div className="absolute right-2">
                {!isExecuting ? (
                  <button
                    onClick={handleStartResearch}
                    disabled={!topic.trim()}
                    className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl font-bold text-xs shadow-lg shadow-indigo-500/25 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                  >
                    <Play className="w-3.5 h-3.5 fill-white" />
                    Launch Research
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                ) : (
                  <button
                    onClick={handleStopResearch}
                    className="flex items-center gap-2 px-5 py-2.5 bg-rose-600 hover:bg-rose-500 text-white rounded-xl font-bold text-xs shadow-lg shadow-rose-500/20 transition-all duration-200 cursor-pointer"
                  >
                    <Square className="w-3.5 h-3.5 fill-white" />
                    Stop
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Advanced Settings Toggle */}
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="mt-4 flex items-center gap-2 text-[11px] text-slate-500 hover:text-slate-300 transition-colors font-medium cursor-pointer"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            {showAdvanced ? 'Hide' : 'Show'} Advanced Settings
          </button>

          {/* Advanced Parameters */}
          {showAdvanced && (
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 animate-fadeInUp">
              {/* Target Length / Word Count */}
              <div className="glass rounded-xl p-3.5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Target Length</span>
                  <span className="text-[11px] font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-md">
                    {targetWordCount <= 1600 ? '4 Pages' : targetWordCount <= 2200 ? '4–6 Pages' : '6 Pages'} ({targetWordCount}w)
                  </span>
                </div>
                <input
                  type="range"
                  min="1400"
                  max="2600"
                  step="200"
                  value={targetWordCount}
                  onChange={(e) => setTargetWordCount(Number(e.target.value))}
                  className="w-full accent-indigo-500"
                />
              </div>

              {/* Self Correction */}
              <div className="glass rounded-xl p-3.5">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1">
                    <Repeat className="w-3 h-3 text-purple-400" /> Quality Threshold
                  </span>
                  <span className="text-[11px] font-mono font-bold text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-md">
                    {selfCorrectionRounds > 0 ? '< 7.5 Score' : 'Off'}
                  </span>
                </div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[9px] text-slate-500">Auto-refines if score is below 7.5</span>
                  <span className="text-[10px] font-mono text-slate-400">{selfCorrectionRounds} loop{selfCorrectionRounds !== 1 ? 's' : ''}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="3"
                  value={selfCorrectionRounds}
                  onChange={(e) => setSelfCorrectionRounds(Number(e.target.value))}
                  className="w-full accent-purple-500"
                />
              </div>

              {/* Search Provider */}
              <div className="glass rounded-xl p-3.5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1">
                    <Globe className="w-3 h-3" /> Search API
                  </span>
                </div>
                <select
                  value={searchProvider}
                  onChange={(e) => setSearchProvider(e.target.value)}
                  className="w-full bg-[#0d1322] border border-slate-800/80 rounded-lg px-3 py-1.5 text-[11px] text-slate-200 focus:outline-none focus:border-indigo-500/50 transition-colors"
                >
                  <option value="tavily">🌐 Tavily Search</option>
                  <option value="serper">🔍 Serper Google</option>
                  <option value="academic">📚 ArXiv Academic</option>
                </select>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div className="glass rounded-2xl p-4 border-rose-500/30 animate-fadeInUp">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-rose-500/20 flex items-center justify-center shrink-0">
              <span className="text-rose-400 text-sm">✕</span>
            </div>
            <div>
              <p className="text-xs font-bold text-rose-400 uppercase tracking-wider mb-0.5">Pipeline Error</p>
              <p className="text-xs text-rose-300/80">{errorMsg}</p>
            </div>
          </div>
        </div>
      )}

      {/* Execution Area */}
      {taskState && (
        <div className="space-y-5 animate-fadeInUp">
          {/* DAG Visualizer (Collapsible) */}
          <WorkflowVisualizer
            steps={taskState.steps || {}}
            pipelineStatus={taskState.status}
            defaultExpanded={taskState.status === 'RUNNING'}
          />

          {/* Live Terminal (Collapsible - Hidden by default) */}
          <div className="glass rounded-2xl overflow-hidden border border-slate-800/60 transition-all duration-300">
            <button
              type="button"
              onClick={() => setShowTerminal((prev) => !prev)}
              className="w-full px-5 py-3.5 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg bg-indigo-500/15">
                  <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                </div>
                <span className="text-xs font-bold text-slate-300 tracking-tight">Agent Stream Terminal</span>
                {isExecuting && <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />}
              </div>

              <div className="flex items-center gap-3">
                <span className="text-[10px] font-mono text-slate-500 bg-slate-800/40 px-2 py-0.5 rounded">
                  {taskState.logs.length} events
                </span>
                <span className="text-xs text-indigo-400 flex items-center gap-1 font-semibold">
                  {showTerminal ? 'Hide Terminal' : 'View Terminal Logs'}
                  {showTerminal ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </span>
              </div>
            </button>

            {showTerminal && (
              <div className="border-t border-slate-800/60 p-4 font-mono text-[11px] text-slate-400 max-h-60 overflow-y-auto space-y-1 bg-[#060a13]/80 animate-fadeInUp">
                {taskState.logs.map((log, idx) => (
                  <div key={idx} className="flex items-start gap-2 py-0.5 hover:bg-white/[0.02] px-2 rounded transition-colors">
                    <span className="text-indigo-500/60 select-none shrink-0">›</span>
                    <span className="text-slate-400/90 break-all">{log}</span>
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            )}
          </div>

          {/* Report */}
          {(taskState.status === 'COMPLETED' || taskState.result?.final_report) && (
            <ReportViewer
              topic={taskState.topic}
              reportMarkdown={taskState.result?.final_report}
              summary={taskState.result?.summary}
              critique={taskState.result?.critique}
            />
          )}
        </div>
      )}

      {/* Empty State */}
      {!taskState && !isExecuting && (
        <div className="flex flex-col items-center justify-center py-20 animate-fadeInUp">
          <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-indigo-500/15 flex items-center justify-center mb-5">
            <Sparkles className="w-7 h-7 text-indigo-500/50" />
          </div>
          <h3 className="text-sm font-bold text-slate-400 mb-1">Ready to Research</h3>
          <p className="text-xs text-slate-600 max-w-sm text-center leading-relaxed">
            Enter a topic above and launch the autonomous multi-agent research pipeline. Your AI agents will collaborate to produce a comprehensive report.
          </p>
        </div>
      )}
    </div>
  );
};
