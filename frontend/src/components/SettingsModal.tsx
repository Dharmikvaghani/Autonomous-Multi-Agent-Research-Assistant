import React, { useState, useEffect } from 'react';
import {
  SlidersHorizontal,
  Key,
  CheckCircle2,
  XCircle,
  Save,
  ShieldCheck,
  Eye,
  EyeOff,
  Loader2,
  Settings2,
  Plus,
  Trash2,
} from 'lucide-react';
import { fetchSettings, updateSettings } from '../api';
import { SettingsState } from '../types';

interface KeyField {
  id: string;
  key: string;
  label: string;
  sub: string;
  placeholder: string;
  canAddMore?: boolean;
}

export const SettingsModal: React.FC = () => {
  const [settings, setSettings] = useState<SettingsState | null>(null);
  const [loading, setLoading] = useState(true);
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState(false);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [extraGroqKeys, setExtraGroqKeys] = useState<string[]>([]);
  const [extraGeminiKeys, setExtraGeminiKeys] = useState<string[]>([]);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await fetchSettings();
      setSettings(data);
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Collect all key values (primary + extra)
    const allKeys: Record<string, string> = {};
    
    // Primary keys
    for (const [fieldKey, value] of Object.entries(keys)) {
      if (value.trim()) {
        allKeys[fieldKey] = value.trim();
      }
    }
    
    // Extra Groq keys
    extraGroqKeys.forEach((val, idx) => {
      if (val.trim()) {
        allKeys[`groq_api_key_${idx + 2}`] = val.trim();
      }
    });
    
    // Extra Gemini keys
    extraGeminiKeys.forEach((val, idx) => {
      if (val.trim()) {
        allKeys[`gemini_api_key_${idx + 2}`] = val.trim();
      }
    });
    
    if (Object.keys(allKeys).length === 0) return;

    setSaving(true);
    try {
      await updateSettings(allKeys);
      setSavedMsg(true);
      setTimeout(() => setSavedMsg(false), 3000);
      await loadSettings();
      setKeys({});
      setExtraGroqKeys([]);
      setExtraGeminiKeys([]);
    } catch {
      alert('Failed to save API keys');
    } finally {
      setSaving(false);
    }
  };

  const primaryKeyFields: KeyField[] = [
    { id: 'groq_api_key', key: 'groq_api_key', label: 'Groq API Key', sub: 'Llama 3 / Mixtral (Primary)', placeholder: 'gsk_...', canAddMore: true },
    { id: 'gemini_api_key', key: 'gemini_api_key', label: 'Gemini API Key', sub: 'Google AI (Primary)', placeholder: 'AIzaSy... or AQ...', canAddMore: true },
    { id: 'nvidia_api_key', key: 'nvidia_api_key', label: 'NVIDIA / DeepSeek API Key', sub: 'DeepSeek v4.1 / v3 / R1 (NIM)', placeholder: 'nvapi-...' },
    { id: 'xai_api_key', key: 'xai_api_key', label: 'xAI / Grok API Key', sub: 'Grok Models (x.ai)', placeholder: 'xai-...' },
    { id: 'openai_api_key', key: 'openai_api_key', label: 'OpenAI API Key', sub: 'GPT-4 / GPT-4o', placeholder: 'sk-proj-...' },
    { id: 'tavily_api_key', key: 'tavily_api_key', label: 'Tavily Search Key', sub: 'Web Search', placeholder: 'tvly-...' },
    { id: 'serper_api_key', key: 'serper_api_key', label: 'Serper API Key', sub: 'Google Search', placeholder: 'serper-...' },
  ];

  const keyCounts = (settings as any)?.key_counts || {};

  const renderKeyInput = (fieldKey: string, placeholder: string, value: string, onChange: (val: string) => void, onRemove?: () => void) => (
    <div className="relative flex gap-2">
      <div className="relative flex-1">
        <input
          type={showKeys[fieldKey] ? 'text' : 'password'}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete="new-password"
          name={`api_credential_${fieldKey}`}
          className="w-full bg-[#0d1322] border border-slate-800/80 rounded-xl px-3 py-2.5 pr-10 text-[11px] text-white placeholder-slate-700 focus:outline-none focus:border-indigo-500/50 transition-colors font-mono"
        />
        <button
          type="button"
          onClick={() => setShowKeys({ ...showKeys, [fieldKey]: !showKeys[fieldKey] })}
          className="absolute right-3 top-2.5 text-slate-600 hover:text-slate-400 transition"
        >
          {showKeys[fieldKey] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
        </button>
      </div>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="p-2.5 text-red-500/60 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );

  return (
    <div className="space-y-6 max-w-4xl mx-auto animate-fadeInUp">
      {/* Header */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-800/60">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-[#0a0f1a] to-indigo-950/20"></div>
        <div className="relative z-10 p-7">
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2.5 bg-indigo-500/15 border border-indigo-500/20 rounded-xl">
              <Settings2 className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-3xl font-extrabold text-white tracking-tight">Settings</h2>
              <p className="text-sm text-slate-400 mt-0.5">Manage LLM models, search providers, and API credentials</p>
            </div>
          </div>
        </div>
      </div>

      {/* Status Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-10">
          <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
        </div>
      ) : settings && (
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
          {Object.entries(settings.api_keys).map(([name, isSet]) => (
            <div
              key={name}
              className={`glass rounded-xl p-3.5 flex flex-col justify-between transition-all ${
                isSet ? 'border-emerald-500/20' : ''
              }`}
            >
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">{name.replace(/_/g, ' ')}</span>
              <div className="flex items-center gap-1.5">
                {isSet ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-[10px] font-bold text-emerald-400">
                      Active
                      {keyCounts[name] > 1 && ` (${keyCounts[name]} keys)`}
                    </span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-3.5 h-3.5 text-slate-600" />
                    <span className="text-[10px] font-medium text-slate-600">Missing</span>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Multi-key Info Banner */}
      <div className="glass rounded-2xl p-4 border border-indigo-500/10">
        <p className="text-[11px] text-slate-400 leading-relaxed">
          <span className="text-indigo-400 font-bold">💡 Multi-Key Rotation:</span>{' '}
          Add multiple Groq or Gemini keys below. When one key's rate limit is reached, 
          the system automatically switches to the next available key — keeping your research running without interruption.
        </p>
      </div>

      {/* API Keys Form */}
      <form onSubmit={handleSave} className="glass rounded-2xl p-6 space-y-5">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-indigo-500/15">
            <Key className="w-4 h-4 text-indigo-400" />
          </div>
          <h3 className="text-sm font-bold text-white">Update API Keys</h3>
        </div>

        <div className="space-y-4">
          {primaryKeyFields.map((field) => (
            <div key={field.id}>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                  {field.label}
                  <span className="text-slate-700 ml-1 normal-case tracking-normal font-normal">— {field.sub}</span>
                </label>
                {field.canAddMore && (
                  <button
                    type="button"
                    onClick={() => {
                      if (field.key === 'groq_api_key' && extraGroqKeys.length < 2) {
                        setExtraGroqKeys([...extraGroqKeys, '']);
                      } else if (field.key === 'gemini_api_key' && extraGeminiKeys.length < 2) {
                        setExtraGeminiKeys([...extraGeminiKeys, '']);
                      }
                    }}
                    className="text-[9px] font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition uppercase tracking-widest"
                  >
                    <Plus className="w-3 h-3" />
                    Add Backup Key
                  </button>
                )}
              </div>
              
              {/* Primary key input */}
              {renderKeyInput(
                field.key,
                field.placeholder,
                keys[field.key] || '',
                (val) => setKeys({ ...keys, [field.key]: val })
              )}

              {/* Extra Groq keys */}
              {field.key === 'groq_api_key' && extraGroqKeys.map((val, idx) => (
                <div key={`groq_extra_${idx}`} className="mt-2">
                  <label className="text-[9px] font-medium text-slate-600 mb-1 block">
                    Backup Key #{idx + 2}
                  </label>
                  {renderKeyInput(
                    `groq_api_key_${idx + 2}`,
                    field.placeholder,
                    val,
                    (newVal) => {
                      const updated = [...extraGroqKeys];
                      updated[idx] = newVal;
                      setExtraGroqKeys(updated);
                    },
                    () => setExtraGroqKeys(extraGroqKeys.filter((_, i) => i !== idx))
                  )}
                </div>
              ))}

              {/* Extra Gemini keys */}
              {field.key === 'gemini_api_key' && extraGeminiKeys.map((val, idx) => (
                <div key={`gemini_extra_${idx}`} className="mt-2">
                  <label className="text-[9px] font-medium text-slate-600 mb-1 block">
                    Backup Key #{idx + 2}
                  </label>
                  {renderKeyInput(
                    `gemini_api_key_${idx + 2}`,
                    field.placeholder,
                    val,
                    (newVal) => {
                      const updated = [...extraGeminiKeys];
                      updated[idx] = newVal;
                      setExtraGeminiKeys(updated);
                    },
                    () => setExtraGeminiKeys(extraGeminiKeys.filter((_, i) => i !== idx))
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>

        <div className="pt-2 flex items-center justify-between">
          {savedMsg ? (
            <span className="text-[11px] font-bold text-emerald-400 flex items-center gap-1.5 animate-fadeInUp">
              <ShieldCheck className="w-4 h-4" /> Keys updated successfully!
            </span>
          ) : <span />}

          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-500/20 flex items-center gap-2 transition cursor-pointer disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </form>
    </div>
  );
};
