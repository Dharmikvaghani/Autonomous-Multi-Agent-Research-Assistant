import React, { useState, useEffect, useRef } from 'react';
import {
  FileText,
  UploadCloud,
  Send,
  BookOpen,
  Bot,
  User,
  Sparkles,
  Loader2,
  MessageSquare,
  File,
} from 'lucide-react';
import { fetchPdfFiles, uploadPdf, chatPdf } from '../api';
import { PdfDocument, PdfChatMessage } from '../types';

interface PdfChatProps {
  currentWorkspace: string;
}

export const PdfChat: React.FC<PdfChatProps> = ({ currentWorkspace }) => {
  const [pdfFiles, setPdfFiles] = useState<PdfDocument[]>([]);
  const [selectedFilename, setSelectedFilename] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);

  const [messages, setMessages] = useState<PdfChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      content: 'Upload a PDF document or select one from the dropdown to begin RAG-powered Q&A. I can answer questions grounded in your document content.',
      timestamp: new Date().toLocaleTimeString()
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeSources, setActiveSources] = useState<any[] | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadPdfs();
  }, [currentWorkspace]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadPdfs = async () => {
    try {
      const files = await fetchPdfFiles(currentWorkspace);
      setPdfFiles(files);
      if (files.length > 0 && !selectedFilename) {
        setSelectedFilename(files[0].filename);
      }
    } catch (err) {
      console.error('Failed to load PDF files:', err);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      const record = await uploadPdf(file, currentWorkspace);
      await loadPdfs();
      setSelectedFilename(record.filename);
      setMessages((prev) => [
        ...prev,
        {
          id: String(Date.now()),
          sender: 'assistant',
          content: `✅ Successfully uploaded and indexed **${record.filename}** (${record.chunk_count} chunks). You can now ask questions about it!`,
          timestamp: new Date().toLocaleTimeString()
        }
      ]);
    } catch (err: any) {
      alert(err.message || 'Failed to upload PDF');
    } finally {
      setIsUploading(false);
    }
  };

  const handleSendQuery = async () => {
    if (!inputQuery.trim() || isGenerating) return;

    const userText = inputQuery.trim();
    setInputQuery('');

    const userMsg: PdfChatMessage = {
      id: String(Date.now()),
      sender: 'user',
      content: userText,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsGenerating(true);

    try {
      const response = await chatPdf(userText, selectedFilename || undefined, currentWorkspace);
      const assistantMsg: PdfChatMessage = {
        id: String(Date.now() + 1),
        sender: 'assistant',
        content: response.answer,
        timestamp: new Date().toLocaleTimeString(),
        sources: response.sources
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: String(Date.now() + 1),
          sender: 'assistant',
          content: '❌ Error: Failed to process query against vector store.',
          timestamp: new Date().toLocaleTimeString()
        }
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeInUp">
      {/* Header */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-800/60">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-950/50 via-[#0a0f1a] to-teal-950/30"></div>
        <div className="absolute top-0 right-0 w-[400px] h-[300px] bg-emerald-600/8 rounded-full blur-[100px] pointer-events-none"></div>

        <div className="relative z-10 p-7">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                  <MessageSquare className="w-3 h-3 text-emerald-400" />
                  <span className="text-[10px] font-bold uppercase text-emerald-400 tracking-wider">RAG Document Chat</span>
                </div>
              </div>
              <h2 className="text-3xl font-extrabold text-white tracking-tight mb-1">
                PDF Chat & Retrieval
              </h2>
              <p className="text-sm text-slate-400 max-w-xl leading-relaxed">
                Chat with uploaded academic literature. Answers are grounded in document content with source citation previews.
              </p>
            </div>

            <label className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl font-bold text-xs shadow-lg shadow-emerald-500/20 cursor-pointer transition shrink-0">
              <UploadCloud className="w-4 h-4" />
              {isUploading ? 'Ingesting...' : 'Upload PDF'}
              <input type="file" accept=".pdf" onChange={handleFileUpload} disabled={isUploading} className="hidden" />
            </label>
          </div>

          {/* PDF Selector */}
          <div className="mt-5 flex items-center gap-3 glass rounded-xl p-3">
            <div className="flex items-center gap-2 text-[11px] text-slate-400 font-semibold shrink-0">
              <File className="w-4 h-4 text-emerald-400" />
              Active Document:
            </div>
            <select
              value={selectedFilename}
              onChange={(e) => setSelectedFilename(e.target.value)}
              className="flex-1 bg-[#0d1322] border border-slate-800/80 rounded-lg px-3 py-2 text-[11px] text-slate-200 focus:outline-none focus:border-emerald-500/50 transition-colors"
            >
              <option value="">🌐 All PDFs in Workspace</option>
              {pdfFiles.map((doc) => (
                <option key={doc.filename} value={doc.filename}>
                  📄 {doc.filename} ({doc.chunk_count} chunks)
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Chat Panel */}
      <div className="glass rounded-2xl overflow-hidden flex flex-col h-[550px]">
        {/* Messages */}
        <div className="flex-1 p-5 overflow-y-auto space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 max-w-2xl ${msg.sender === 'user' ? 'ml-auto flex-row-reverse' : ''} animate-fadeInUp`}
            >
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                msg.sender === 'user'
                  ? 'bg-gradient-to-br from-indigo-600 to-purple-600 text-white'
                  : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
              }`}>
                {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              <div className={`rounded-2xl p-4 text-[12px] leading-relaxed ${
                msg.sender === 'user'
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-tr-sm'
                  : 'bg-[#111827]/80 border border-slate-800/60 text-slate-200 rounded-tl-sm'
              }`}>
                <div className="whitespace-pre-wrap">{msg.content}</div>

                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-700/40">
                    <button
                      onClick={() => setActiveSources(activeSources === msg.sources ? null : msg.sources)}
                      className="text-[11px] font-bold text-emerald-400 flex items-center gap-1.5 hover:underline cursor-pointer"
                    >
                      <BookOpen className="w-3.5 h-3.5" />
                      {msg.sources.length} Source Chunks
                    </button>

                    {activeSources === msg.sources && (
                      <div className="mt-2 space-y-2">
                        {msg.sources.map((src, i) => (
                          <div key={i} className="bg-[#060a13] border border-slate-800/60 rounded-xl p-3 text-[11px] text-slate-300 space-y-1.5">
                            <div className="flex items-center justify-between text-indigo-400 font-bold gap-2">
                              <span className="truncate">{src.title || src.source_file}</span>
                              <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] shrink-0 font-mono">
                                {src.similarity || 'Vector Match'}
                              </span>
                            </div>
                            {src.section && (
                              <div className="flex items-center gap-1.5 text-[10px] text-purple-400 font-semibold">
                                <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
                                Section: {src.section}
                              </div>
                            )}
                            <div className="text-slate-400 font-mono text-[10px] bg-slate-900/60 p-2 rounded-lg border border-slate-800/40 leading-relaxed">
                              "{src.excerpt}"
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-2 text-[10px] opacity-40 text-right">{msg.timestamp}</div>
              </div>
            </div>
          ))}
          {isGenerating && (
            <div className="flex gap-3 animate-fadeInUp">
              <div className="w-8 h-8 rounded-xl bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
              <div className="bg-[#111827]/80 border border-slate-800/60 rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex items-center gap-2 text-[11px] text-slate-400">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                  Searching vector store and generating response...
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-slate-800/60">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendQuery()}
              placeholder="Ask a question about your document..."
              className="flex-1 bg-[#0d1322]/80 border border-slate-800/60 rounded-xl px-4 py-3 text-[12px] text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500/50 transition-colors"
            />
            <button
              onClick={handleSendQuery}
              disabled={!inputQuery.trim() || isGenerating}
              className="px-5 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-emerald-500/20 disabled:opacity-40 transition cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
