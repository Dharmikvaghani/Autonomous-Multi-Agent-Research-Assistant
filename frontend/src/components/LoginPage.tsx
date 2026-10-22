import React, { useState } from 'react';
import {
  Zap,
  Lock,
  User as UserIcon,
  Mail,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  Bot,
  BrainCircuit,
  FileText,
  AlertCircle,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { loginUser, registerUser } from '../api';
import { User } from '../types';

interface LoginPageProps {
  onLoginSuccess: (user: User) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const formatError = (err: any, fallback: string): string => {
    const msg = err?.message || fallback;
    if (msg.includes('aborted') || msg.includes('abort') || msg.includes('signal is aborted')) {
      return 'Connection timed out. Please check that the Prism AI backend is running.';
    }
    if (msg.includes('Failed to fetch') || msg.includes('NetworkError')) {
      return 'Unable to connect to Prism AI server. Please verify backend is running.';
    }
    return msg;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    if (isRegister) {
      if (!username.trim() || !email.trim() || !password.trim()) {
        setErrorMsg('Please fill in all required fields.');
        return;
      }
      if (password !== confirmPassword) {
        setErrorMsg('Passwords do not match.');
        return;
      }
      if (password.length < 6) {
        setErrorMsg('Password must be at least 6 characters long.');
        return;
      }

      setLoading(true);
      try {
        const res = await registerUser(username.trim(), email.trim(), password, fullName.trim() || undefined);
        setSuccessMsg('Account created successfully! Logging you in...');
        setTimeout(() => {
          onLoginSuccess(res.user);
        }, 600);
      } catch (err: any) {
        setErrorMsg(formatError(err, 'Registration failed.'));
      } finally {
        setLoading(false);
      }
    } else {
      if (!username.trim() || !password.trim()) {
        setErrorMsg('Please enter your username or email and password.');
        return;
      }

      setLoading(true);
      try {
        const res = await loginUser(username.trim(), password);
        setSuccessMsg(`Welcome, ${res.user.full_name || res.user.username}!`);
        setTimeout(() => {
          onLoginSuccess(res.user);
        }, 500);
      } catch (err: any) {
        setErrorMsg(formatError(err, 'Invalid username or password.'));
      } finally {
        setLoading(false);
      }
    }
  };

  const handleQuickDemo = async () => {
    setErrorMsg(null);
    setUsername('admin');
    setPassword('password123');
    setLoading(true);
    try {
      const res = await loginUser('admin', 'password123');
      setSuccessMsg('Quick Demo Login successful!');
      setTimeout(() => {
        onLoginSuccess(res.user);
      }, 400);
    } catch (err: any) {
      setErrorMsg(formatError(err, 'Quick Demo Login failed.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#060a13] text-slate-100 flex flex-col justify-center items-center p-4 sm:p-6 relative overflow-hidden selection:bg-indigo-500/40 selection:text-white">
      {/* Background ambient lighting effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[650px] h-[550px] bg-gradient-to-tr from-indigo-600/15 via-purple-600/15 to-pink-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute -bottom-20 -left-20 w-[450px] h-[450px] bg-indigo-600/10 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute -top-20 -right-20 w-[450px] h-[450px] bg-purple-600/10 rounded-full blur-[100px] pointer-events-none" />

      {/* Main Container */}
      <div className="w-full max-w-4xl relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch my-auto">
        {/* Left Side: Brand & Feature Highlights */}
        <div className="lg:col-span-5 bg-gradient-to-br from-[#0c1222] via-[#090e1a] to-[#0d1424] border border-slate-800/80 rounded-3xl p-7 lg:p-8 flex flex-col justify-between shadow-2xl relative overflow-hidden">
          <div className="relative z-10">
            {/* Logo */}
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/30 animate-pulseGlow">
                <Zap className="w-6 h-6 text-white drop-shadow" />
              </div>
              <div>
                <h1 className="font-extrabold text-2xl text-white tracking-tight leading-none">
                  PRISM AI
                </h1>
                <p className="text-[11px] text-indigo-400 font-semibold mt-1 tracking-wider uppercase">
                  Research Intelligence Platform
                </p>
              </div>
            </div>

            {/* Tagline */}
            <h2 className="text-xl font-bold text-slate-100 tracking-tight leading-snug mb-3">
              Autonomous Multi-Agent Academic & Technical Research
            </h2>
            <p className="text-xs text-slate-400 leading-relaxed mb-6">
              Orchestrates 9 autonomous agents to investigate, verify, and compile concise, publication-grade 4–6 page synthesis reports backed by ChromaDB vector memory.
            </p>

            {/* Feature Bullets */}
            <div className="space-y-3">
              <div className="flex items-start gap-3 bg-[#080d1a]/70 border border-slate-800/60 rounded-xl p-3">
                <div className="w-7 h-7 rounded-lg bg-indigo-500/15 flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-4 h-4 text-indigo-400" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-200">9 Autonomous Agents</h4>
                  <p className="text-[11px] text-slate-400 leading-tight mt-0.5">
                    Planner, multi-subtopic researchers, draft consolidator, summarizer, and critic.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 bg-[#080d1a]/70 border border-slate-800/60 rounded-xl p-3">
                <div className="w-7 h-7 rounded-lg bg-purple-500/15 flex items-center justify-center shrink-0 mt-0.5">
                  <FileText className="w-4 h-4 text-purple-400" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-200">Calibrated 4–6 Page Reports</h4>
                  <p className="text-[11px] text-slate-400 leading-tight mt-0.5">
                    Fast processing, token-budgeted synthesis without API exhaustion.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 bg-[#080d1a]/70 border border-slate-800/60 rounded-xl p-3">
                <div className="w-7 h-7 rounded-lg bg-emerald-500/15 flex items-center justify-center shrink-0 mt-0.5">
                  <BrainCircuit className="w-4 h-4 text-emerald-400" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-200">Vector Knowledge & PDF RAG</h4>
                  <p className="text-[11px] text-slate-400 leading-tight mt-0.5">
                    ChromaDB semantic search with PDF document parsing and chat.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Security Badge */}
          <div className="pt-6 mt-6 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
            <span className="flex items-center gap-1.5 font-medium">
              <ShieldCheck className="w-4 h-4 text-emerald-400" /> SQLite Database Auth
            </span>
            <span className="font-mono text-[10px]">v2.0 Enterprise</span>
          </div>
        </div>

        {/* Right Side: Auth Form Card */}
        <div className="lg:col-span-7 bg-[#0a0f1c]/90 border border-slate-800/80 rounded-3xl p-7 lg:p-9 shadow-2xl backdrop-blur-xl flex flex-col justify-between">
          <div>
            {/* Header Tabs */}
            <div className="flex items-center justify-between border-b border-slate-800/70 pb-4 mb-6">
              <div>
                <h3 className="text-xl font-bold text-white tracking-tight">
                  {isRegister ? 'Create Researcher Account' : 'Welcome Back'}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  {isRegister
                    ? 'Register your account stored in the local SQLite database'
                    : 'Sign in to access your research dashboard'}
                </p>
              </div>

              <div className="flex bg-[#070b16] p-1 rounded-xl border border-slate-800/80">
                <button
                  type="button"
                  onClick={() => {
                    setIsRegister(false);
                    setErrorMsg(null);
                    setSuccessMsg(null);
                  }}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                    !isRegister
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsRegister(true);
                    setErrorMsg(null);
                    setSuccessMsg(null);
                  }}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                    isRegister
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Register
                </button>
              </div>
            </div>

            {/* Quick Demo Button (Sign In Mode) */}
            {!isRegister && (
              <div className="mb-6 p-3.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/25 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-fadeInUp">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-indigo-600/20 flex items-center justify-center shrink-0">
                    <Sparkles className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-indigo-200">Database Demo Account</p>
                    <p className="text-[11px] text-slate-400">
                      Pre-configured: <code className="text-indigo-300 font-mono">admin</code> / <code className="text-indigo-300 font-mono">password123</code>
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleQuickDemo}
                  disabled={loading}
                  className="w-full sm:w-auto px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold rounded-xl shadow-md shadow-indigo-500/20 transition-all flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                  1-Click Sign In
                </button>
              </div>
            )}

            {/* Error & Success Feedback Banners */}
            {errorMsg && (
              <div className="mb-5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center gap-2.5 text-rose-300 text-xs animate-fadeInUp">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{errorMsg}</span>
              </div>
            )}
            {successMsg && (
              <div className="mb-5 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-2.5 text-emerald-300 text-xs animate-fadeInUp">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                <span>{successMsg}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {isRegister && (
                <div className="space-y-1.5 animate-fadeInUp">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                    Full Name
                  </label>
                  <div className="relative flex items-center">
                    <UserIcon className="w-4 h-4 text-slate-500 absolute left-3.5 pointer-events-none" />
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="e.g., Dr. Jane Doe"
                      className="w-full bg-[#070b16] border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
                    />
                  </div>
                </div>
              )}

              {/* Username or Email */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                  {isRegister ? 'Username *' : 'Username or Email *'}
                </label>
                <div className="relative flex items-center">
                  <UserIcon className="w-4 h-4 text-slate-500 absolute left-3.5 pointer-events-none" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder={isRegister ? 'Choose a unique username' : 'Enter username or email'}
                    className="w-full bg-[#070b16] border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              {isRegister && (
                <div className="space-y-1.5 animate-fadeInUp">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                    Email Address *
                  </label>
                  <div className="relative flex items-center">
                    <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 pointer-events-none" />
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@organization.com"
                      className="w-full bg-[#070b16] border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
                    />
                  </div>
                </div>
              )}

              {/* Password */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                  Password *
                </label>
                <div className="relative flex items-center">
                  <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 pointer-events-none" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={isRegister ? 'Minimum 6 characters' : 'Enter your password'}
                    className="w-full bg-[#070b16] border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              {isRegister && (
                <div className="space-y-1.5 animate-fadeInUp">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                    Confirm Password *
                  </label>
                  <div className="relative flex items-center">
                    <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 pointer-events-none" />
                    <input
                      type="password"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Confirm your password"
                      className="w-full bg-[#070b16] border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
                    />
                  </div>
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-3 px-5 bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl font-bold text-xs tracking-wide shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    {isRegister ? 'Create Database Account' : 'Sign In to Prism'}
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Toggle between Login and Register */}
          <div className="mt-6 pt-4 border-t border-slate-800/60 text-center text-xs text-slate-400">
            {isRegister ? (
              <p>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => setIsRegister(false)}
                  className="text-indigo-400 font-bold hover:underline cursor-pointer"
                >
                  Sign in here
                </button>
              </p>
            ) : (
              <p>
                Need a new account?{' '}
                <button
                  type="button"
                  onClick={() => setIsRegister(true)}
                  className="text-indigo-400 font-bold hover:underline cursor-pointer"
                >
                  Register in database
                </button>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
