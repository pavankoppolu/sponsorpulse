import axios from 'axios';
import type {
  Company,
  Contact,
  Outreach,
  KanbanBoard,
  GmailAuthStatus,
  McpStatus,
  KanbanStats,
  CompanyQueryParams,
  KanbanStage,
} from '../types';

const api = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const discoveryApi = {
  syncFundingFeeds: async (): Promise<{ status: string; new_companies?: number; message?: string }> => {
    const res = await api.post('/api/discovery/sync');
    return res.data;
  },
  getCompanies: async (params?: CompanyQueryParams): Promise<Company[]> => {
    const res = await api.get('/api/discovery/companies', { params });
    return res.data;
  },
  getCompany: async (id: number): Promise<Company> => {
    const res = await api.get(`/api/discovery/companies/${id}`);
    return res.data;
  },
};

export const enrichmentApi = {
  enrichCompany: async (companyId: number): Promise<{ message: string; outreach?: Outreach; contacts?: Contact[] }> => {
    const res = await api.post(`/api/enrichment/enrich/${companyId}`);
    return res.data;
  },
  getMcpStatus: async (): Promise<McpStatus> => {
    const res = await api.get('/api/enrichment/mcp-status');
    return res.data;
  },
  getContacts: async (companyId: number): Promise<Contact[]> => {
    const res = await api.get(`/api/enrichment/contacts/${companyId}`);
    return res.data;
  },
};

export const kanbanApi = {
  getKanbanBoard: async (): Promise<KanbanBoard> => {
    const res = await api.get('/api/kanban/board');
    return res.data;
  },
  moveKanbanCard: async (outreachId: number, stage: KanbanStage): Promise<Outreach> => {
    const res = await api.put(`/api/kanban/move/${outreachId}`, { stage }, { params: { stage } });
    return res.data;
  },
  getKanbanStats: async (): Promise<KanbanStats> => {
    const res = await api.get('/api/kanban/stats');
    return res.data;
  },
};

export const outreachApi = {
  generateEmail: async (outreachId: number, refinement?: string): Promise<Outreach> => {
    const payload = refinement ? { refinement } : {};
    const res = await api.post(`/api/outreach/generate-email/${outreachId}`, payload, {
      params: refinement ? { refinement } : undefined,
    });
    return res.data;
  },
  updateDraft: async (outreachId: number, subject: string, body: string): Promise<Outreach> => {
    const res = await api.put(`/api/outreach/draft/${outreachId}`, {
      subject,
      body,
      email_subject: subject,
      email_body: body,
    });
    return res.data;
  },
  approveOutreach: async (outreachId: number): Promise<Outreach> => {
    const res = await api.post(`/api/outreach/approve/${outreachId}`);
    return res.data;
  },
  sendOutreach: async (outreachId: number): Promise<{ message: string; outreach: Outreach; message_id?: string }> => {
    const res = await api.post(`/api/outreach/send/${outreachId}`);
    return res.data;
  },
  syncReplies: async (): Promise<{ message: string; updated_count?: number; replies?: any[] }> => {
    const res = await api.post('/api/outreach/sync-replies');
    return res.data;
  },
  getOutreaches: async (stage?: KanbanStage): Promise<Outreach[]> => {
    const res = await api.get('/api/outreach/', {
      params: stage ? { stage } : undefined,
    });
    return res.data;
  },
};

export const authApi = {
  getGmailStatus: async (): Promise<GmailAuthStatus> => {
    const res = await api.get('/api/auth/google/status');
    return res.data;
  },
  getConfigStatus: async (): Promise<{
    credentials_present: boolean;
    token_present: boolean;
    authenticated: boolean;
    email: string | null;
    credentials_path: string;
  }> => {
    const res = await api.get('/api/auth/google/config-status');
    return res.data;
  },
  getGmailAuthUrl: async (): Promise<{ url: string; auth_url?: string }> => {
    const res = await api.get('/api/auth/google/url');
    return res.data;
  },
  devConnectGmail: async (email?: string): Promise<{ status: string; message: string; email?: string }> => {
    const res = await api.post('/api/auth/google/dev-connect', null, { params: { email } });
    return res.data;
  },
  revokeGmail: async (): Promise<{ status: string; message: string }> => {
    const res = await api.post('/api/auth/google/revoke');
    return res.data;
  },
};

export default api;
