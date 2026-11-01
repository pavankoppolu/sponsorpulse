import React, { useState } from 'react';
import { Draggable } from '@hello-pangea/dnd';
import {
  Sparkles,
  Search,
  FileEdit,
  Send,
  RefreshCw,
  MessageSquare,
  User,
  DollarSign,
  Clock,
  ExternalLink,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import type { Outreach } from '../types';
import { enrichmentApi, outreachApi } from '../services/api';

interface KanbanCardProps {
  outreach: Outreach;
  index: number;
  onRefresh: () => void;
  onOpenDraftModal: (outreach: Outreach) => void;
}

function formatRelativeTime(dateString?: string | null): string {
  if (!dateString) return 'recently';
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return 'just now';
  const minutes = Math.floor(diffInSeconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return date.toLocaleDateString();
}

export const KanbanCard: React.FC<KanbanCardProps> = ({
  outreach,
  index,
  onRefresh,
  onOpenDraftModal,
}) => {
  const [loading, setLoading] = useState(false);

  const { company, contact, kanban_stage, updated_at, last_reply_snippet } = outreach;

  const handleEnrich = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setLoading(true);
      await enrichmentApi.enrichCompany(outreach.company_id);
      onRefresh();
    } catch (err: any) {
      console.error('Failed to enrich company:', err);
      alert(err.response?.data?.detail || 'Enrichment failed. Please check MCP server connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateEmail = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setLoading(true);
      await outreachApi.generateEmail(outreach.id);
      onRefresh();
    } catch (err: any) {
      console.error('Failed to generate email:', err);
      alert(err.response?.data?.detail || 'Email generation failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleSendNow = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!contact?.email) {
      alert('Cannot send: Contact does not have a valid email address.');
      return;
    }
    const confirmed = window.confirm(
      `Send email to ${contact.first_name} ${contact.last_name} (${contact.email}) via Gmail?`
    );
    if (!confirmed) return;

    try {
      setLoading(true);
      await outreachApi.sendOutreach(outreach.id);
      onRefresh();
    } catch (err: any) {
      console.error('Failed to send outreach:', err);
      alert(err.response?.data?.detail || 'Failed to send outreach. Ensure Gmail is authenticated.');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckReplies = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setLoading(true);
      await outreachApi.syncReplies();
      onRefresh();
    } catch (err: any) {
      console.error('Failed to sync replies:', err);
      alert('Failed to check for reply messages.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Draggable draggableId={String(outreach.id)} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          onClick={() => {
            if (['DRAFTED', 'READY_TO_SEND', 'SENT', 'REPLIED'].includes(kanban_stage)) {
              onOpenDraftModal(outreach);
            }
          }}
          className={`group relative rounded-xl p-3.5 mb-2.5 select-none transition-all duration-150 border ${
            snapshot.isDragging
              ? 'bg-slate-800 border-teal-500/60 shadow-xl scale-[1.02] rotate-1 z-50 ring-2 ring-teal-500/20'
              : 'bg-slate-900/70 hover:bg-slate-850 border-slate-800/80 hover:border-slate-700 shadow-sm hover:shadow-md'
          }`}
        >
          {/* Top Row: Company Logo Initials & Funding */}
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex items-center space-x-2 truncate">
              <div className="w-5 h-5 rounded-md bg-slate-800 border border-slate-700/70 text-[10px] font-bold text-slate-300 flex items-center justify-center flex-shrink-0 uppercase">
                {company?.name ? company.name.charAt(0) : '#'}
              </div>
              <h4
                className="text-xs font-semibold text-slate-100 truncate group-hover:text-teal-300 transition-colors"
                title={company?.name}
              >
                {company?.name || `Outreach #${outreach.id}`}
              </h4>
            </div>

            {company?.funding_amount && (
              <span className="flex-shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <DollarSign className="w-2.5 h-2.5 mr-0.5" />
                {company.funding_amount}
              </span>
            )}
          </div>

          {/* Contact Details (if enriched) */}
          {contact ? (
            <div className="flex items-center space-x-2 text-xs text-slate-300 mb-2.5 bg-slate-950/40 px-2.5 py-1.5 rounded-lg border border-slate-800/80">
              <User className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
              <div className="truncate">
                <span className="font-medium text-slate-200">
                  {contact.first_name} {contact.last_name}
                </span>
                {contact.title && (
                  <span className="text-slate-400 text-[10px] block truncate">
                    {contact.title}
                  </span>
                )}
              </div>
            </div>
          ) : (
            kanban_stage === 'DISCOVERED' && (
              <p className="text-[11px] text-slate-400 line-clamp-1 italic mb-2.5">
                {company?.summary || 'Pending contact discovery and enrichment'}
              </p>
            )
          )}

          {/* Reply snippet preview if stage is REPLIED */}
          {kanban_stage === 'REPLIED' && last_reply_snippet && (
            <div className="mb-2.5 p-2 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-xs text-emerald-200">
              <div className="flex items-center gap-1 font-semibold text-[10px] text-emerald-400 uppercase tracking-wider mb-0.5">
                <MessageSquare className="w-3 h-3" />
                <span>Latest Partner Reply</span>
              </div>
              <p className="line-clamp-2 text-[11px] text-slate-300 italic">
                "{last_reply_snippet}"
              </p>
            </div>
          )}

          {/* Action Row */}
          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between gap-2">
            <div className="flex items-center space-x-1 text-[10px] text-slate-500" title={`Updated: ${updated_at}`}>
              <Clock className="w-3 h-3 text-slate-500" />
              <span>{formatRelativeTime(updated_at)}</span>
            </div>

            {/* Stage-Specific Action Button */}
            <div>
              {kanban_stage === 'DISCOVERED' && (
                <button
                  type="button"
                  onClick={handleEnrich}
                  disabled={loading}
                  className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-800 hover:bg-slate-750 text-slate-200 border border-slate-700 hover:border-slate-600 flex items-center space-x-1 transition-all active:scale-95 shadow-sm"
                >
                  {loading ? (
                    <Loader2 className="w-3 h-3 animate-spin text-teal-400" />
                  ) : (
                    <Search className="w-3 h-3 text-teal-400" />
                  )}
                  <span>Enrich Contact</span>
                </button>
              )}

              {kanban_stage === 'ENRICHED' && (
                <button
                  type="button"
                  onClick={handleGenerateEmail}
                  disabled={loading}
                  className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-800 hover:bg-slate-750 text-teal-300 border border-teal-500/30 hover:border-teal-500/50 flex items-center space-x-1 transition-all active:scale-95 shadow-sm"
                >
                  {loading ? (
                    <Loader2 className="w-3 h-3 animate-spin text-teal-400" />
                  ) : (
                    <Sparkles className="w-3 h-3 text-teal-400" />
                  )}
                  <span>Generate Email</span>
                </button>
              )}

              {kanban_stage === 'DRAFTED' && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenDraftModal(outreach);
                  }}
                  className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-800 hover:bg-slate-750 text-amber-300 border border-amber-500/30 hover:border-amber-500/50 flex items-center space-x-1 transition-all active:scale-95"
                >
                  <FileEdit className="w-3 h-3 text-amber-400" />
                  <span>Review Draft</span>
                </button>
              )}

              {kanban_stage === 'READY_TO_SEND' && (
                <button
                  type="button"
                  onClick={handleSendNow}
                  disabled={loading}
                  className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm flex items-center space-x-1 transition-all active:scale-95"
                >
                  {loading ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Send className="w-3 h-3" />
                  )}
                  <span>Send Now</span>
                </button>
              )}

              {kanban_stage === 'SENT' && (
                <button
                  type="button"
                  onClick={handleCheckReplies}
                  disabled={loading}
                  className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700/80 flex items-center space-x-1 transition-all"
                  title="Check for inbox replies"
                >
                  {loading ? (
                    <Loader2 className="w-3 h-3 animate-spin text-teal-400" />
                  ) : (
                    <RefreshCw className="w-3 h-3 text-teal-400" />
                  )}
                  <span>Check Replies</span>
                </button>
              )}

              {kanban_stage === 'REPLIED' && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenDraftModal(outreach);
                  }}
                  className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-emerald-950/40 text-emerald-300 border border-emerald-500/30 flex items-center space-x-1 hover:bg-emerald-900/40 transition-colors"
                >
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span>View Thread</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </Draggable>
  );
};

export default KanbanCard;
