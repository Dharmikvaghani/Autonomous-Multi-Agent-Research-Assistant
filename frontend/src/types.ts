export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  role: string;
  created_at?: string;
  last_login?: string;
}

export interface AuthResponse {
  success: boolean;
  token: string;
  user: User;
  message: string;
}

export interface StepInfo {
  name: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'SKIPPED';
  duration: number;
  error?: string;
}

export interface ResearchResult {
  final_report?: string;
  summary?: string;
  critique?: any;
  pipeline_status: string;
  tasks: Record<string, StepInfo>;
}

export interface ResearchTaskState {
  task_id: string;
  status: string;
  topic: string;
  logs: string[];
  steps: Record<string, StepInfo>;
  result?: ResearchResult;
  duration?: number;
}

export interface MemoryItem {
  id: string;
  topic: string;
  summary: string;
  critique: any;
  full_research: string;
  metadata?: Record<string, any>;
  created_at?: string;
}

export interface PdfDocument {
  filename: string;
  title: string;
  chunk_count: number;
  sections: string[];
  table_count: number;
  reference_count: number;
  summary: string;
  timestamp: string;
  workspace: string;
}

export interface PdfSource {
  source_file: string;
  title: string;
  section: string;
  similarity: string;
  excerpt: string;
}

export interface PdfChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: PdfSource[];
}

export interface SettingsState {
  api_keys: {
    groq: boolean;
    gemini: boolean;
    openai: boolean;
    tavily: boolean;
    serper: boolean;
    xai: boolean;
    nvidia?: boolean;
    deepseek?: boolean;
  };
  key_counts?: {
    groq: number;
    gemini: number;
  };
  available_workspaces: string[];
}
