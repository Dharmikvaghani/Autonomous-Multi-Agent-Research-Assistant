import React, { useState, useEffect } from 'react';
import { StepInfo } from '../types';
import {
  CheckCircle2,
  Loader2,
  XCircle,
  Clock,
  GitFork,
  ArrowRight,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface WorkflowVisualizerProps {
  steps: Record<string, StepInfo>;
  pipelineStatus: string;
  defaultExpanded?: boolean;
}

export const WorkflowVisualizer: React.FC<WorkflowVisualizerProps> = ({ steps, pipelineStatus, defaultExpanded }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(defaultExpanded ?? (pipelineStatus === 'RUNNING'));

  useEffect(() => {
    if (defaultExpanded !== undefined) {
      setIsExpanded(defaultExpanded);
    }
  }, [defaultExpanded]);
  const dagPhases = [
    {
      phase: 'Planning',
      nodes: [{ id: 'planner', label: 'Strategic Planner', emoji: '🧠' }],
    },
    {
      phase: 'Research',
      nodes: [
        { id: 'researcher_0', label: 'Researcher A', emoji: '🔬' },
        { id: 'researcher_1', label: 'Researcher B', emoji: '🔍' },
        { id: 'researcher_2', label: 'Researcher C', emoji: '📊' },
      ],
    },
    {
      phase: 'Synthesis',
      nodes: [
        { id: 'draft_consolidation', label: 'Draft Merge', emoji: '📝' },
        { id: 'rag_enhancement', label: 'RAG Enhancement', emoji: '🧬' },
      ],
    },
    {
      phase: 'Quality',
      nodes: [
        { id: 'summarizer', label: 'Summarizer', emoji: '📋' },
        { id: 'critic', label: 'AI Critic', emoji: '⚖️' },
        { id: 'self_correction', label: 'Self-Correction', emoji: '🔄' },
      ],
    },
    {
      phase: 'Output',
      nodes: [
        { id: 'report_generator', label: 'Report Generator', emoji: '📄' },
        { id: 'memory_storage', label: 'Memory Archive', emoji: '💾' },
      ],
    },
  ];

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'RUNNING':
        return <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />;
      case 'COMPLETED':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'FAILED':
        return <XCircle className="w-3.5 h-3.5 text-rose-400" />;
      default:
        return <Clock className="w-3.5 h-3.5 text-slate-600" />;
    }
  };

  const getNodeStyle = (status?: string) => {
    switch (status) {
      case 'RUNNING':
        return 'border-indigo-500/40 bg-indigo-500/8 shadow-lg shadow-indigo-500/10';
      case 'COMPLETED':
        return 'border-emerald-500/30 bg-emerald-500/5';
      case 'FAILED':
        return 'border-rose-500/30 bg-rose-500/5';
      default:
        return 'border-slate-800/60 bg-[#0d1322]/40 opacity-50';
    }
  };

  const getPhaseColor = () => {
    return 'text-slate-600';
  };

  return (
    <div className="glass rounded-2xl overflow-hidden border border-slate-800/60 transition-all duration-300">
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="w-full p-4 px-5 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-purple-500/15">
            <GitFork className="w-4 h-4 text-purple-400" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-white tracking-tight flex items-center gap-2">
              Agent Workflow Pipeline
              <span className="text-[11px] font-normal text-slate-500 hidden sm:inline">
                (9 Autonomous Agents)
              </span>
            </h3>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className={`px-2.5 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-widest ${
            pipelineStatus === 'RUNNING' ? 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/20' :
            pipelineStatus === 'COMPLETED' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' :
            pipelineStatus === 'FAILED' ? 'bg-rose-500/15 text-rose-400 border border-rose-500/20' :
            'bg-slate-800/50 text-slate-500 border border-slate-800'
          }`}>
            {pipelineStatus}
          </span>
          <span className="text-xs text-purple-400 flex items-center gap-1 font-semibold">
            {isExpanded ? 'Hide Pipeline' : 'View Pipeline'}
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </span>
        </div>
      </button>

      {/* Horizontal pipeline flow (collapsible) */}
      {isExpanded && (
        <div className="p-5 pt-1 border-t border-slate-800/40 animate-fadeInUp">
          <div className="flex items-stretch gap-2 overflow-x-auto pt-3 pb-2">
            {dagPhases.map((phase, phaseIdx) => (
              <React.Fragment key={phase.phase}>
                <div className="flex flex-col gap-2 min-w-[140px]">
                  <span className={`text-[9px] font-bold uppercase tracking-widest text-center ${getPhaseColor()}`}>
                    {phase.phase}
                  </span>
                  {phase.nodes.map((node) => {
                    const info = steps[node.id];
                    const status = info?.status || 'PENDING';
                    const duration = info?.duration;
                    return (
                      <div
                        key={node.id}
                        className={`px-3 py-2.5 rounded-xl border transition-all duration-300 flex items-center gap-2.5 ${getNodeStyle(status)}`}
                      >
                        <span className="text-sm">{node.emoji}</span>
                        <div className="min-w-0 flex-1">
                          <h4 className="text-[11px] font-semibold text-slate-300 truncate">{node.label}</h4>
                          {duration !== undefined && duration > 0 && (
                            <span className="text-[9px] font-mono text-slate-500">{duration.toFixed(1)}s</span>
                          )}
                        </div>
                        {getStatusIcon(status)}
                      </div>
                    );
                  })}
                </div>
                {phaseIdx < dagPhases.length - 1 && (
                  <div className="flex items-center px-1 self-center">
                    <ArrowRight className="w-4 h-4 text-slate-700" />
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
