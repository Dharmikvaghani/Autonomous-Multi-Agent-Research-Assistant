import React, { useState, useEffect } from 'react';
import {
  BrainCircuit,
  Search,
  Trash2,
  Award,
  Clock,
  RefreshCw,
  ExternalLink,
  X,
  Database,
  Loader2,
} from 'lucide-react';
import { fetchMemories, deleteMemory } from '../api';
import { MemoryItem } from '../types';
import { ReportViewer } from './ReportViewer';

interface MemoryBankProps {
  currentWorkspace: string;
}

export const MemoryBank: React.FC<MemoryBankProps> = ({ currentWorkspace }) => {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedMemory, setSelectedMemory] = useState<MemoryItem | null>(null);

  const loadMemories = async () => {
    try {
      setLoading(true);
      const items = await fetchMemories(searchQuery, currentWorkspace);
      setMemories(items);
    } catch (err) {
      console.error('Failed to load memories:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMemories();
  }, [searchQuery, currentWorkspace]);

  const handleDelete = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Delete this memory record?')) return;
    const ok = await deleteMemory(docId, currentWorkspace);
    if (ok) {
      if (selectedMemory?.id === docId) setSelectedMemory(null);
      loadMemories();
    }
  };

  return (
    <div className="space-y-6 animate-fadeInUp">
      {/* Header */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-800/60">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-950/50 via-[#0a0f1a] to-indigo-950/30"></div>
        <div className="absolute top-0 right-0 w-[400px] h-[300px] bg-purple-600/8 rounded-full blur-[100px] pointer-events-none"></div>

        <div className="relative z-10 p-7">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20">
                  <Database className="w-3 h-3 text-purple-400" />
                  <span className="text-[10px] font-bold uppercase text-purple-400 tracking-wider">Vector Knowledge Store</span>
                </div>
              </div>
              <h2 className="text-3xl font-extrabold text-white tracking-tight mb-1">
                AI Memory Bank
              </h2>
              <p className="text-sm text-slate-400 max-w-xl leading-relaxed">
                All research sessions are vector-encoded into ChromaDB. Agents query this vault to prevent redundant work and build on past knowledge.
              </p>
            </div>

            <button
              onClick={loadMemories}
              className="flex items-center gap-2 px-4 py-2.5 glass glass-hover rounded-xl text-[11px] font-semibold text-slate-300 transition shrink-0 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {/* Search */}
          <div className="relative group">
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-purple-500/20 via-indigo-500/20 to-purple-500/20 blur-sm opacity-0 group-focus-within:opacity-100 transition-opacity duration-300"></div>
            <div className="relative">
              <Search className="w-5 h-5 text-slate-500 absolute left-4 top-3.5 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search memories semantically..."
                className="w-full bg-[#0d1322]/90 border border-slate-700/60 rounded-2xl pl-12 pr-4 py-3.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-purple-500/60 transition-colors"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Memory Grid */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin mb-3" />
          <p className="text-xs text-slate-500">Loading memory records...</p>
        </div>
      ) : memories.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 animate-fadeInUp">
          <div className="w-16 h-16 rounded-3xl bg-purple-500/10 border border-purple-500/15 flex items-center justify-center mb-5">
            <BrainCircuit className="w-7 h-7 text-purple-500/50" />
          </div>
          <h3 className="text-sm font-bold text-slate-400 mb-1">No Memories Found</h3>
          <p className="text-xs text-slate-600 max-w-sm text-center leading-relaxed">
            No research records exist in workspace '{currentWorkspace}'. Run a research session to populate the memory bank.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {memories.map((mem, idx) => {
            const dateStr = mem.created_at ? new Date(mem.created_at).toLocaleDateString() : 'Recent';
            const score = mem.critique?.score || 'N/A';

            return (
              <div
                key={mem.id}
                onClick={() => setSelectedMemory(mem)}
                className="glass glass-hover rounded-2xl p-5 transition-all duration-200 cursor-pointer group flex flex-col justify-between animate-fadeInUp"
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-lg bg-slate-800/60 text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {dateStr}
                    </span>
                    <button
                      onClick={(e) => handleDelete(mem.id, e)}
                      className="p-1.5 rounded-lg text-slate-600 hover:text-rose-400 hover:bg-rose-500/10 transition opacity-0 group-hover:opacity-100"
                      title="Delete"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <h3 className="font-bold text-sm text-slate-200 group-hover:text-white transition line-clamp-2 mb-2">
                    {mem.topic}
                  </h3>

                  <p className="text-[11px] text-slate-500 line-clamp-3 leading-relaxed mb-4">
                    {mem.summary || mem.full_research}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-800/40 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <Award className="w-3.5 h-3.5 text-amber-400/60" />
                    <span className="font-semibold text-slate-500 text-[11px]">Score: {score}</span>
                  </div>
                  <span className="text-[11px] font-semibold text-indigo-500 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all group-hover:translate-x-1">
                    View <ExternalLink className="w-3 h-3" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail Modal */}
      {selectedMemory && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4" onClick={() => setSelectedMemory(null)}>
          <div className="bg-[#0a0f1a] border border-slate-700/60 rounded-3xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="p-5 border-b border-slate-800/60 flex items-center justify-between">
              <div>
                <span className="text-[10px] uppercase font-bold text-purple-400 tracking-widest">Memory Record</span>
                <h3 className="font-extrabold text-base text-white mt-0.5">{selectedMemory.topic}</h3>
              </div>
              <button
                onClick={() => setSelectedMemory(null)}
                className="p-2 text-slate-500 hover:text-white rounded-xl hover:bg-slate-800 transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              <ReportViewer
                topic={selectedMemory.topic}
                reportMarkdown={selectedMemory.full_research}
                summary={selectedMemory.summary}
                critique={selectedMemory.critique}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
