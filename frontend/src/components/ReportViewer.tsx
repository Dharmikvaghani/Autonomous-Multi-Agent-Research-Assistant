import React, { useState } from 'react';
import { marked } from 'marked';
import {
  Download,
  Copy,
  Check,
  Award,
  FileCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Lightbulb,
  BookOpen,
  FileText,
  BarChart3,
  FileCode,
} from 'lucide-react';
import { exportReportPdf, exportReportLatex, exportReportBibtex } from '../api';

interface ReportViewerProps {
  topic: string;
  reportMarkdown?: string;
  summary?: string;
  critique?: any;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({
  topic,
  reportMarkdown,
  summary,
  critique,
}) => {
  const [copied, setCopied] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadingLatex, setDownloadingLatex] = useState(false);
  const [downloadingBibtex, setDownloadingBibtex] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState<'report' | 'summary' | 'critique'>('report');

  if (!reportMarkdown && !summary && !critique) {
    return (
      <div className="glass rounded-2xl p-16 text-center animate-fadeInUp">
        <div className="w-14 h-14 rounded-2xl bg-slate-800/50 flex items-center justify-center mx-auto mb-4">
          <FileCheck className="w-7 h-7 text-slate-600" />
        </div>
        <h3 className="text-sm font-bold text-slate-400">No Report Generated Yet</h3>
        <p className="text-xs text-slate-600 mt-2 max-w-md mx-auto leading-relaxed">
          Start a research session above. When the multi-agent pipeline finishes, your comprehensive report will appear here.
        </p>
      </div>
    );
  }

  const handleCopyMarkdown = () => {
    if (reportMarkdown) {
      navigator.clipboard.writeText(reportMarkdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadPdf = async () => {
    if (!reportMarkdown) return;
    try {
      setDownloading(true);
      const blob = await exportReportPdf(topic, reportMarkdown);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${topic.toLowerCase().replace(/[^a-z0-9]/g, '_')}_report.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert('Failed to download PDF');
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadLatex = async () => {
    if (!reportMarkdown) return;
    try {
      setDownloadingLatex(true);
      const blob = await exportReportLatex(topic, reportMarkdown);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${topic.toLowerCase().replace(/[^a-z0-9]/g, '_')}_paper.tex`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert('Failed to download LaTeX');
    } finally {
      setDownloadingLatex(false);
    }
  };

  const handleDownloadBibtex = async () => {
    try {
      setDownloadingBibtex(true);
      const blob = await exportReportBibtex(topic, reportMarkdown);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${topic.toLowerCase().replace(/[^a-z0-9]/g, '_')}_references.bib`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert('Failed to download BibTeX');
    } finally {
      setDownloadingBibtex(false);
    }
  };

  const tabs = [
    { id: 'report', label: 'Full Report', icon: FileText },
    { id: 'summary', label: 'Executive Summary', icon: BookOpen },
    { id: 'critique', label: 'AI Critique', icon: BarChart3 },
  ] as const;

  const renderCritiqueSection = () => {
    if (!critique) return <p className="text-slate-500 text-xs">No critique evaluation available.</p>;

    const critData = typeof critique === 'object' ? critique : {};
    const score = critData.score || 'N/A';
    const grade = critData.research_grade || 'A';
    const strengths = critData.strengths || [];
    const weaknesses = critData.weaknesses || [];
    const missingAreas = critData.missing_research_areas || critData.missing_areas || [];

    return (
      <div className="space-y-5 animate-fadeInUp">
        {/* Score Card */}
        <div className="relative overflow-hidden rounded-2xl border border-amber-500/20">
          <div className="absolute inset-0 bg-gradient-to-r from-amber-950/30 via-transparent to-emerald-950/20"></div>
          <div className="relative p-5 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-amber-500/15 border border-amber-500/25 flex items-center justify-center">
                <Award className="w-6 h-6 text-amber-400" />
              </div>
              <div>
                <h4 className="font-bold text-sm text-white">Research Quality Scorecard</h4>
                <p className="text-[11px] text-slate-500 mt-0.5">Evaluated for rigor, coverage, and accuracy</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-[9px] uppercase font-bold tracking-widest text-slate-500">Score</div>
                <div className="text-2xl font-extrabold text-amber-400">{score}</div>
              </div>
              {grade && (
                <span className="px-3 py-1.5 rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-600/10 text-amber-300 font-extrabold text-sm border border-amber-500/25">
                  {grade}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Strengths & Weaknesses */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="glass rounded-xl p-4 border-emerald-500/15">
            <h5 className="font-bold text-xs text-emerald-400 flex items-center gap-2 mb-3">
              <CheckCircle2 className="w-4 h-4" /> Strengths
            </h5>
            <ul className="space-y-2">
              {Array.isArray(strengths) && strengths.length > 0 ? (
                strengths.map((s: string, idx: number) => (
                  <li key={idx} className="text-[11px] text-slate-300 bg-emerald-500/5 border border-emerald-500/10 rounded-lg p-2.5 flex items-start gap-2">
                    <span className="text-emerald-400 font-bold mt-0.5">✓</span>
                    <span>{s}</span>
                  </li>
                ))
              ) : (
                <p className="text-xs text-slate-600">Comprehensive coverage across all subtopics.</p>
              )}
            </ul>
          </div>

          <div className="glass rounded-xl p-4 border-rose-500/15">
            <h5 className="font-bold text-xs text-rose-400 flex items-center gap-2 mb-3">
              <XCircle className="w-4 h-4" /> Weaknesses
            </h5>
            <ul className="space-y-2">
              {Array.isArray(weaknesses) && weaknesses.length > 0 ? (
                weaknesses.map((w: string, idx: number) => (
                  <li key={idx} className="text-[11px] text-slate-300 bg-rose-500/5 border border-rose-500/10 rounded-lg p-2.5 flex items-start gap-2">
                    <span className="text-rose-400 font-bold mt-0.5">✕</span>
                    <span>{w}</span>
                  </li>
                ))
              ) : (
                <p className="text-xs text-slate-600">No major critical flaws detected.</p>
              )}
            </ul>
          </div>
        </div>

        {/* Missing Areas */}
        {Array.isArray(missingAreas) && missingAreas.length > 0 && (
          <div className="glass rounded-xl p-4 border-amber-500/15">
            <h5 className="font-bold text-xs text-amber-400 flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4" /> Knowledge Gaps
            </h5>
            <div className="space-y-2">
              {missingAreas.map((m: string, idx: number) => (
                <div key={idx} className="text-[11px] text-slate-300 bg-amber-500/5 border border-amber-500/10 rounded-lg p-2.5 flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>{m}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="glass rounded-2xl overflow-hidden animate-fadeInUp">
      {/* Toolbar */}
      <div className="px-5 py-3 border-b border-slate-800/60 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1 bg-[#060a13] p-1 rounded-xl border border-slate-800/60">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id)}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[11px] font-bold transition-all ${
                  activeSubTab === tab.id
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/20'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={handleCopyMarkdown}
            className="flex items-center gap-1.5 px-2.5 py-1.5 glass glass-hover rounded-xl text-[11px] font-semibold text-slate-300 transition cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied!' : 'Copy'}
          </button>

          <button
            onClick={handleDownloadPdf}
            disabled={downloading}
            className="flex items-center gap-1 px-3 py-1.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-[11px] font-bold shadow-sm shadow-indigo-500/20 transition disabled:opacity-50 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            {downloading ? 'Exporting...' : 'PDF'}
          </button>

          <button
            onClick={handleDownloadLatex}
            disabled={downloadingLatex}
            title="Download Academic LaTeX Source (.tex)"
            className="flex items-center gap-1 px-2.5 py-1.5 glass glass-hover hover:border-indigo-500/50 text-indigo-300 hover:text-white rounded-xl text-[11px] font-semibold transition disabled:opacity-50 cursor-pointer"
          >
            <FileCode className="w-3.5 h-3.5 text-indigo-400" />
            {downloadingLatex ? 'Generating...' : 'LaTeX (.tex)'}
          </button>

          <button
            onClick={handleDownloadBibtex}
            disabled={downloadingBibtex}
            title="Download BibTeX Bibliography (.bib)"
            className="flex items-center gap-1 px-2.5 py-1.5 glass glass-hover hover:border-purple-500/50 text-purple-300 hover:text-white rounded-xl text-[11px] font-semibold transition disabled:opacity-50 cursor-pointer"
          >
            <BookOpen className="w-3.5 h-3.5 text-purple-400" />
            {downloadingBibtex ? 'Generating...' : 'BibTeX (.bib)'}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 max-h-[700px] overflow-y-auto">
        {activeSubTab === 'report' && (
          <div
            className="prose prose-invert max-w-none prose-headings:font-bold prose-headings:text-white prose-p:text-slate-300 prose-p:leading-relaxed prose-li:text-slate-300 prose-code:text-indigo-300 prose-code:bg-slate-800/60 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded"
            dangerouslySetInnerHTML={{ __html: marked(reportMarkdown || 'No report available.') }}
          />
        )}

        {activeSubTab === 'summary' && (
          <div className="glass rounded-xl p-5">
            <h4 className="font-bold text-xs text-indigo-400 uppercase tracking-widest mb-3">Executive Summary</h4>
            <div
              className="prose prose-invert max-w-none text-slate-300 text-sm leading-relaxed"
              dangerouslySetInnerHTML={{ __html: marked(summary || 'No summary available.') }}
            />
          </div>
        )}

        {activeSubTab === 'critique' && renderCritiqueSection()}
      </div>
    </div>
  );
};
