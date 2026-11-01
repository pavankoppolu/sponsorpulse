import React, { useState, useEffect } from 'react';
import {
  X,
  Sparkles,
  Send,
  CheckCircle,
  AlertTriangle,
  Building2,
  User,
  Mail,
  Loader2,
  DollarSign,
  Calendar,
  Save,
} from 'lucide-react';
import type { Outreach } from '../types';
import { outreachApi } from '../services/api';

interface EmailDraftModalProps {
  outreach: Outreach | null;
  isOpen: boolean;
  onClose: () => void;
  onRefresh: () => void;
}

export const EmailDraftModal: React.FC<EmailDraftModalProps> = ({
  outreach,
  isOpen,
  onClose,
  onRefresh,
}) => {
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [refinement, setRefinement] = useState('');
  const [pillar, setPillar] = useState<'CORPORATE' | 'CAMPUS' | 'COMMUNITY'>(
    (outreach?.pillar as any) || 'CORPORATE'
  );
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    if (outreach) {
      setSubject(outreach.email_subject || '');
      setBody(outreach.email_body || '');
      setPillar((outreach.pillar as any) || 'CORPORATE');
      setRefinement('');
      setStatusMessage(null);
    }
  }, [outreach, isOpen]);

  if (!isOpen || !outreach) return null;

  const company = outreach.company;
  const contact = outreach.contact;

  const handleSaveDraft = async () => {
    try {
      setIsSaving(true);
      await outreachApi.updateDraft(outreach.id, subject, body);
      setStatusMessage({ text: 'Draft updated successfully.', type: 'success' });
      onRefresh();
    } catch (err: any) {
      console.error('Failed to update draft:', err);
      setStatusMessage({
        text: err.response?.data?.detail || 'Failed to save draft changes.',
        type: 'error',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleRegenerate = async () => {
    try {
      setIsRegenerating(true);
      setStatusMessage(null);
      const pillarInstruction = `Target Outreach Pillar: ${pillar}. Please customize the angle for ${
        pillar === 'CAMPUS'
          ? 'Campus Outreach (partnering with colleges to identify and recruit student talent, campus placement drives, and hackathons)'
          : pillar === 'COMMUNITY'
          ? 'Community Outreach (connecting with developer communities and student clubs for workshops, mentorship, and career support)'
          : 'Corporate Outreach (building relationships with funded companies for talent placement, campus drives, and sponsorships)'
      }. ${refinement.trim()}`;

      const updated = await outreachApi.generateEmail(outreach.id, pillarInstruction);
      setSubject(updated.email_subject || '');
      setBody(updated.email_body || '');
      setStatusMessage({ text: `Pitch tailored for ${pillar} Outreach via Gemini!`, type: 'success' });
      onRefresh();
    } catch (err: any) {
      console.error('Failed to regenerate email:', err);
      setStatusMessage({
        text: err.response?.data?.detail || 'Failed to regenerate email with Gemini.',
        type: 'error',
      });
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleApprove = async () => {
    try {
      setIsApproving(true);
      setStatusMessage(null);
      // Auto-save changes first
      await outreachApi.updateDraft(outreach.id, subject, body);
      await outreachApi.approveOutreach(outreach.id);
      onRefresh();
      onClose();
    } catch (err: any) {
      console.error('Failed to approve outreach:', err);
      setStatusMessage({
        text: err.response?.data?.detail || 'Failed to approve outreach.',
        type: 'error',
      });
      setIsApproving(false);
    }
  };

  const handleSend = async () => {
    const confirmSend = window.confirm(
      `Are you sure you want to send this outreach immediately via Gmail to ${
        contact?.email || 'the contact'
      }?`
    );
    if (!confirmSend) return;

    try {
      setIsSending(true);
      setStatusMessage(null);
      // Auto-save any manual edits prior to sending
      await outreachApi.updateDraft(outreach.id, subject, body);
      await outreachApi.sendOutreach(outreach.id);
      onRefresh();
      onClose();
    } catch (err: any) {
      console.error('Failed to send outreach:', err);
      setStatusMessage({
        text: err.response?.data?.detail || 'Failed to send outreach via Gmail. Ensure Gmail is connected.',
        type: 'error',
      });
      setIsSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200 overflow-y-auto">
      <div className="relative my-auto bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-4 sm:px-6 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-900/80 flex-shrink-0">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Mail className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                Outreach Draft: {company?.name || 'Company'}
              </h2>
              <p className="text-xs text-slate-400">
                Review and customize the sponsorship inquiry before approving or dispatching.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Domain Safety Banner */}
        <div className="bg-amber-950/40 border-b border-amber-600/30 px-6 py-2.5 flex items-center space-x-3 text-amber-300 text-xs font-medium">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span>
            Domain Safety Notice: Review email carefully before sending. Avoid unvetted bulk outreach to preserve domain sender reputation.
          </span>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1 custom-scrollbar">
          {/* Status Message */}
          {statusMessage && (
            <div
              className={`p-3 rounded-lg text-xs font-medium border flex items-center justify-between ${
                statusMessage.type === 'success'
                  ? 'bg-emerald-950/50 border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-950/50 border-rose-500/30 text-rose-300'
              }`}
            >
              <span>{statusMessage.text}</span>
              <button
                onClick={() => setStatusMessage(null)}
                className="ml-2 hover:underline opacity-80"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Context Cards: Company & Contact */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Company Context */}
            <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5 space-y-1.5 text-xs">
              <div className="flex items-center text-slate-300 font-semibold gap-1.5">
                <Building2 className="w-4 h-4 text-blue-400" />
                <span>Company Details</span>
              </div>
              <div className="text-slate-200 font-medium text-sm">{company?.name}</div>
              <div className="flex flex-wrap items-center gap-2 text-slate-400">
                {company?.funding_amount && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-emerald-950/50 border border-emerald-500/30 text-emerald-400 text-[11px] font-medium">
                    <DollarSign className="w-3 h-3 mr-0.5" />
                    {company.funding_amount}
                  </span>
                )}
                {company?.funding_date && (
                  <span className="inline-flex items-center text-slate-400 text-[11px]">
                    <Calendar className="w-3 h-3 mr-1 opacity-70" />
                    {new Date(company.funding_date).toLocaleDateString()}
                  </span>
                )}
                {company?.domain && (
                  <span className="text-slate-400 text-[11px]">
                    {company.domain}
                  </span>
                )}
              </div>
              {company?.summary && (
                <p className="text-slate-400 text-xs line-clamp-2 mt-1 italic">
                  "{company.summary}"
                </p>
              )}
            </div>

            {/* Contact Details */}
            <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5 space-y-1.5 text-xs">
              <div className="flex items-center text-slate-300 font-semibold gap-1.5">
                <User className="w-4 h-4 text-purple-400" />
                <span>Target Contact</span>
              </div>
              {contact ? (
                <>
                  <div className="text-slate-200 font-medium text-sm">
                    {contact.first_name} {contact.last_name}
                  </div>
                  <div className="text-slate-300 text-xs">
                    {contact.title || 'Role not specified'}
                  </div>
                  <div className="text-slate-400 text-[11px] flex items-center gap-1 font-mono">
                    <Mail className="w-3 h-3 text-slate-500" />
                    {contact.email || 'No verified email'}
                  </div>
                </>
              ) : (
                <div className="text-slate-500 italic py-2">
                  No enriched contact associated yet.
                </div>
              )}
            </div>
          </div>

          {/* Outreach Pillar Selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
              <span>Outreach Pillar & Mission Angle:</span>
              <span className="text-[11px] text-slate-400 font-normal">Select which pillar guides this pitch</span>
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setPillar('CORPORATE')}
                className={`py-2 px-3 rounded-xl border text-xs font-semibold transition-all flex items-center justify-center space-x-1.5 ${
                  pillar === 'CORPORATE'
                    ? 'bg-indigo-600/30 border-indigo-500 text-indigo-300 ring-1 ring-indigo-500/50'
                    : 'bg-slate-800/60 border-slate-700/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                <span>🏢 Corporate</span>
                <span className="text-[10px] opacity-70 hidden sm:inline">(Placements)</span>
              </button>

              <button
                type="button"
                onClick={() => setPillar('CAMPUS')}
                className={`py-2 px-3 rounded-xl border text-xs font-semibold transition-all flex items-center justify-center space-x-1.5 ${
                  pillar === 'CAMPUS'
                    ? 'bg-purple-600/30 border-purple-500 text-purple-300 ring-1 ring-purple-500/50'
                    : 'bg-slate-800/60 border-slate-700/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                <span>🎓 Campus</span>
                <span className="text-[10px] opacity-70 hidden sm:inline">(Colleges)</span>
              </button>

              <button
                type="button"
                onClick={() => setPillar('COMMUNITY')}
                className={`py-2 px-3 rounded-xl border text-xs font-semibold transition-all flex items-center justify-center space-x-1.5 ${
                  pillar === 'COMMUNITY'
                    ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300 ring-1 ring-emerald-500/50'
                    : 'bg-slate-800/60 border-slate-700/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                <span>🤝 Community</span>
                <span className="text-[10px] opacity-70 hidden sm:inline">(Opportunities)</span>
              </button>
            </div>
          </div>

          {/* Email Subject Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 block">
              Email Subject
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="e.g. Partnership Opportunities with ..."
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder-slate-500 transition-all font-medium"
            />
          </div>

          {/* Email Body Textarea */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300 block">
                Email Message Body
              </label>
              <button
                type="button"
                onClick={handleSaveDraft}
                disabled={isSaving}
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
              >
                {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                Save Changes
              </button>
            </div>
            <textarea
              rows={9}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Write or review your personalized email outreach here..."
              className="w-full px-3.5 py-3 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder-slate-500 transition-all font-sans resize-y"
            />
          </div>

          {/* Regenerate with Gemini Section */}
          <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/20 space-y-3">
            <div className="flex items-center space-x-2 text-xs font-semibold text-indigo-300">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span>Refine or Regenerate with Gemini AI</span>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={refinement}
                onChange={(e) => setRefinement(e.target.value)}
                placeholder="Optional instructions (e.g. 'Make it shorter and emphasize student hackathon sponsorship')"
                className="flex-1 px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleRegenerate();
                  }
                }}
              />
              <button
                onClick={handleRegenerate}
                disabled={isRegenerating}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white text-xs font-medium flex items-center space-x-1.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-indigo-950"
              >
                {isRegenerating ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Thinking...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 text-indigo-200" />
                    <span>Regenerate</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-4 sm:px-6 py-3 border-t border-slate-800 bg-slate-900/90 flex flex-wrap items-center justify-between gap-2.5 flex-shrink-0">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 rounded-lg text-slate-400 hover:text-slate-200 text-xs font-medium hover:bg-slate-800 transition-colors"
          >
            Cancel
          </button>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleApprove}
              disabled={isApproving || isSending}
              className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 active:scale-95 text-slate-200 border border-slate-700 text-xs font-medium flex items-center space-x-1.5 transition-all disabled:opacity-50"
            >
              {isApproving ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Approving...</span>
                </>
              ) : (
                <>
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Approve & Move to Ready</span>
                </>
              )}
            </button>

            <button
              onClick={handleSend}
              disabled={isSending || isApproving || !contact?.email}
              className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white text-xs font-medium flex items-center space-x-1.5 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              title={!contact?.email ? 'Cannot send without a contact email address' : 'Send email immediately via Gmail'}
            >
              {isSending ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Sending via Gmail...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Send Immediately via Gmail</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmailDraftModal;
