import { MemoryItem, PdfDocument, PdfChatMessage, SettingsState, User, AuthResponse } from './types';

const API_BASE = '/api';

export function getStoredToken(): string | null {
  return localStorage.getItem('prism_auth_token');
}

export function setStoredToken(token: string | null) {
  if (token) {
    localStorage.setItem('prism_auth_token', token);
  } else {
    localStorage.removeItem('prism_auth_token');
  }
}

export function getAuthHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
  const token = getStoredToken();
  const headers: Record<string, string> = { ...extraHeaders };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 8000): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => {
    try {
      controller.abort(new Error(`Connection timed out after ${Math.round(timeoutMs / 1000)}s`));
    } catch {
      controller.abort();
    }
  }, timeoutMs);

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return res;
  } catch (err: any) {
    if (err?.name === 'AbortError' || err?.message?.includes('aborted') || err?.message?.includes('abort')) {
      throw new Error(`Server connection timed out (${Math.round(timeoutMs / 1000)}s). Please ensure the backend is running.`);
    }
    if (err?.message?.includes('Failed to fetch') || err?.message?.includes('NetworkError')) {
      throw new Error('Unable to connect to Prism AI server. Please verify backend is online.');
    }
    throw err;
  } finally {
    clearTimeout(id);
  }
}

export async function loginUser(username: string, password: string): Promise<AuthResponse> {
  const res = await fetchWithTimeout(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  }, 15000);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(err.detail || 'Invalid username or password');
  }
  const data: AuthResponse = await res.json();
  if (data.token) {
    setStoredToken(data.token);
  }
  return data;
}

export async function registerUser(username: string, email: string, password: string, fullName?: string): Promise<AuthResponse> {
  const res = await fetchWithTimeout(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password, full_name: fullName }),
  }, 15000);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
    throw new Error(err.detail || 'Registration failed');
  }
  const data: AuthResponse = await res.json();
  if (data.token) {
    setStoredToken(data.token);
  }
  return data;
}

export async function fetchCurrentUser(): Promise<User | null> {
  const token = getStoredToken();
  if (!token) return null;
  try {
    const res = await fetchWithTimeout(
      `${API_BASE}/auth/me`,
      { headers: getAuthHeaders() },
      3500
    );
    if (!res.ok) {
      if (res.status === 401 || res.status === 403) {
        setStoredToken(null);
      }
      return null;
    }
    return await res.json();
  } catch {
    return null;
  }
}

export async function logoutUser(): Promise<void> {
  const token = getStoredToken();
  if (token) {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: getAuthHeaders(),
    }).catch(() => {});
  }
  setStoredToken(null);
  localStorage.removeItem('prism_user_profile');
}

export async function startResearch(
  topic: string,
  targetWordCount = 2000,
  selfCorrectionRounds = 1,
  searchProvider = 'tavily',
  workspace = 'default'
) {
  const res = await fetch(`${API_BASE}/research/start`, {
    method: 'POST',
    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      topic,
      target_word_count: targetWordCount,
      self_correction_rounds: selfCorrectionRounds,
      search_provider: searchProvider,
      workspace,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to start research' }));
    throw new Error(err.detail || 'Failed to start research');
  }
  return res.json();
}

export async function getResearchStatus(taskId: string) {
  const res = await fetch(`${API_BASE}/research/status/${taskId}`);
  if (!res.ok) throw new Error('Failed to fetch research status');
  return res.json();
}

export async function fetchMemories(query?: string, workspace = 'default'): Promise<MemoryItem[]> {
  const params = new URLSearchParams({ workspace });
  if (query) params.append('query', query);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);
  try {
    const res = await fetch(`${API_BASE}/memory?${params.toString()}`, {
      signal: controller.signal
    });
    if (!res.ok) throw new Error('Failed to fetch memories');
    return await res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function deleteMemory(docId: string, workspace = 'default'): Promise<boolean> {
  const res = await fetch(`${API_BASE}/memory/${docId}?workspace=${workspace}`, {
    method: 'DELETE',
  });
  return res.ok;
}

export async function fetchPdfFiles(workspace = 'default'): Promise<PdfDocument[]> {
  const res = await fetch(`${API_BASE}/pdf/files?workspace=${workspace}`);
  if (!res.ok) throw new Error('Failed to list PDFs');
  return res.json();
}

export async function uploadPdf(file: File, workspace = 'default'): Promise<PdfDocument> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('workspace', workspace);

  const res = await fetch(`${API_BASE}/pdf/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to upload PDF' }));
    throw new Error(err.detail || 'Failed to upload PDF');
  }
  return res.json();
}

export async function chatPdf(query: string, filename?: string, workspace = 'default') {
  const res = await fetch(`${API_BASE}/pdf/chat?workspace=${workspace}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, filename, top_k: 4 }),
  });
  if (!res.ok) throw new Error('PDF Chat failed');
  return res.json();
}

export async function exportReportPdf(title: string, markdownContent: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/export/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, markdown_content: markdownContent }),
  });
  if (!res.ok) throw new Error('Failed to generate PDF');
  return res.blob();
}

export async function exportReportLatex(title: string, markdownContent: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/export/latex`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, markdown_content: markdownContent }),
  });
  if (!res.ok) throw new Error('Failed to generate LaTeX');
  return res.blob();
}

export async function exportReportBibtex(title: string, markdownContent?: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/export/bibtex`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, markdown_content: markdownContent }),
  });
  if (!res.ok) throw new Error('Failed to generate BibTeX');
  return res.blob();
}

export async function fetchSettings(): Promise<SettingsState> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/settings`, {}, 3500);
    if (!res.ok) throw new Error('Failed to fetch settings');
    return await res.json();
  } catch {
    return {
      api_keys: {
        groq: false,
        gemini: false,
        openai: false,
        tavily: false,
        serper: false,
        xai: false,
        nvidia: false,
        deepseek: false,
      },
      key_counts: { groq: 0, gemini: 0 },
      available_workspaces: ['default'],
    };
  }
}

export async function updateSettings(keys: Record<string, string>): Promise<boolean> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(keys),
  });
  return res.ok;
}
