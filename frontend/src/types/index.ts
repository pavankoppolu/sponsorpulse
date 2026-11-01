export type KanbanStage =
  | "DISCOVERED"
  | "ENRICHED"
  | "DRAFTED"
  | "READY_TO_SEND"
  | "SENT"
  | "REPLIED"
  | "CLOSED";

export type OutreachPillar = "CORPORATE" | "CAMPUS" | "COMMUNITY";

export interface Company {
  id: number;
  name: string;
  domain: string | null;
  funding_amount: string | null;
  funding_date: string | null;
  source_url: string | null;
  summary: string | null;
  created_at: string;
}

export interface Contact {
  id: number;
  company_id: number;
  first_name: string;
  last_name: string;
  email: string | null;
  title: string | null;
  linkedin_url: string | null;
}

export interface Outreach {
  id: number;
  company_id: number;
  contact_id: number | null;
  kanban_stage: KanbanStage;
  pillar?: OutreachPillar;
  email_subject: string | null;
  email_body: string | null;
  gmail_message_id: string | null;
  gmail_thread_id: string | null;
  last_reply_snippet: string | null;
  sent_at: string | null;
  updated_at: string;
  company?: Company;
  contact?: Contact;
}

export interface KanbanBoard {
  [stage: string]: Outreach[];
}

export interface GmailAuthStatus {
  authenticated: boolean;
  email: string | null;
}

export interface McpStatus {
  connected: boolean;
  server_url?: string;
  details?: Record<string, any>;
}

export interface KanbanStats {
  total: number;
  by_stage: Record<KanbanStage | string, number>;
}

export interface CompanyQueryParams {
  search?: string;
  min_funding?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  skip?: number;
}
