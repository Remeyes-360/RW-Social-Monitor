import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
});

export interface Stats {
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  crisis: number;
  negative_pct: number;
  positive_pct: number;
  period_hours: number;
}

export interface AlertLevel {
  level: 'CALME' | 'VIGILANCE' | 'TENSION' | 'CRISE';
  negative_pct: number;
  crisis_count: number;
  total_mentions: number;
}

export interface Platform {
  platform: string;
  count: number;
}

export interface Narratif {
  narratif: string;
  count: number;
}

export interface TimelinePoint {
  hour: string;
  positif: number;
  negatif: number;
  neutre: number;
  crise: number;
}

export interface TopAccount {
  author: string;
  platform: string;
  count: number;
}

export interface Mention {
  id: number;
  platform: string;
  content: string;
  author: string;
  sentiment: string;
  is_crisis: boolean;
  narratifs: string[];
  collected_at: string;
  url: string;
}

export const dashboardApi = {
  getStats: (hours = 24) => api.get<Stats>(`/api/dashboard/stats?hours=${hours}`),
  getAlertLevel: () => api.get<AlertLevel>('/api/dashboard/alert-level'),
  getPlatforms: (hours = 24) => api.get<Platform[]>(`/api/dashboard/platforms?hours=${hours}`),
  getNaratifs: (hours = 24) => api.get<Narratif[]>(`/api/dashboard/narratifs?hours=${hours}`),
  getTimeline: (hours = 24) => api.get<TimelinePoint[]>(`/api/dashboard/timeline?hours=${hours}`),
  getTopAccounts: (hours = 24) => api.get<TopAccount[]>(`/api/dashboard/top-accounts?hours=${hours}`),
  getComentions: (hours = 24) => api.get(`/api/dashboard/comentions?hours=${hours}`),
};

export const mentionsApi = {
  getAll: (params?: Record<string, any>) => api.get<Mention[]>('/api/mentions/', { params }),
  getCrisis: (hours = 24) => api.get<Mention[]>(`/api/mentions/crisis?hours=${hours}`),
};

export default api;
