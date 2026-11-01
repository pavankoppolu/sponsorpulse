import React, { useState, useEffect, useMemo } from 'react';
import {
  Users,
  Search,
  Mail,
  Linkedin,
  Building,
  ExternalLink,
  Sparkles,
  Send,
  CheckCircle2,
  Filter,
} from 'lucide-react';
import { outreachApi, enrichmentApi } from '../services/api';
import type { Outreach } from '../types';

interface ContactsDirectoryProps {
  onOpenDraftModal: (outreach: Outreach) => void;
}

export const ContactsDirectory: React.FC<ContactsDirectoryProps> = ({ onOpenDraftModal }) => {
  const [outreaches, setOutreaches] = useState<Outreach[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRole, setSelectedRole] = useState('ALL');

  const fetchOutreaches = async () => {
    try {
      setLoading(true);
      const data = await outreachApi.getOutreaches();
      // Only show outreaches that have an identified contact
      setOutreaches(data.filter((o) => o.contact != null));
    } catch (err) {
      console.error('Failed to load contacts directory:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOutreaches();
  }, []);

  const roles = useMemo(() => {
    const set = new Set<string>();
    outreaches.forEach((o) => {
      if (o.contact?.title) set.add(o.contact.title);
    });
    return Array.from(set);
  }, [outreaches]);

  const filtered = useMemo(() => {
    return outreaches.filter((o) => {
      const c = o.contact;
      const comp = o.company;
      if (!c) return false;

      const fullName = `${c.first_name} ${c.last_name}`.toLowerCase();
      const compName = (comp?.name || '').toLowerCase();
      const title = (c.title || '').toLowerCase();
      const email = (c.email || '').toLowerCase();
      const search = searchTerm.toLowerCase();

      if (searchTerm && !fullName.includes(search) && !compName.includes(search) && !title.includes(search) && !email.includes(search)) {
        return false;
      }

      if (selectedRole !== 'ALL' && c.title !== selectedRole) {
        return false;
      }

      return true;
    });
  }, [outreaches, searchTerm, selectedRole]);

  return (
    <div className="flex flex-col h-full bg-slate-950 p-6 overflow-hidden">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800 flex-shrink-0">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2.5">
            <Users className="w-4 h-4 text-teal-400" />
            <span>Corporate Contacts Directory</span>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700/60">
              {filtered.length} decision-makers
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Verified engineering leads, CTOs, and talent heads identified via Enricho MCP
          </p>
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by name, company, title..."
              className="pl-9 pr-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-700/80 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-teal-500/50 w-64 shadow-sm"
            />
          </div>

          {roles.length > 0 && (
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-700/80 text-xs text-slate-300 focus:outline-none focus:ring-1 focus:ring-teal-500/50 shadow-sm"
            >
              <option value="ALL">All Roles ({roles.length})</option>
              {roles.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Directory Table */}
      <div className="flex-1 overflow-auto mt-4 rounded-xl border border-slate-800/80 bg-slate-900/30">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-slate-400 text-xs">
            Loading directory...
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-slate-400 text-xs space-y-2">
            <Users className="w-8 h-8 text-slate-600" />
            <p className="font-medium text-slate-300">No contacts identified yet</p>
            <p className="text-[11px] text-slate-500">
              Click &quot;Enrich &amp; Add to Board&quot; on any company in the Funding Discovery feed.
            </p>
          </div>
        ) : (
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 text-slate-400 text-[11px] uppercase tracking-wider font-semibold border-b border-slate-800 sticky top-0 backdrop-blur z-10">
              <tr>
                <th className="py-3 px-4">Contact</th>
                <th className="py-3 px-4">Company</th>
                <th className="py-3 px-4">Role / Title</th>
                <th className="py-3 px-4">Email</th>
                <th className="py-3 px-4">Pipeline Stage</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {filtered.map((outreach) => {
                const c = outreach.contact!;
                const comp = outreach.company;
                return (
                  <tr key={outreach.id} className="hover:bg-slate-800/30 transition-colors">
                    {/* Contact Name & LinkedIn */}
                    <td className="py-3.5 px-4 font-semibold text-slate-100">
                      <div className="flex items-center space-x-2">
                        <div className="w-7 h-7 rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 flex items-center justify-center font-bold text-xs flex-shrink-0">
                          {c.first_name[0]}
                          {c.last_name[0]}
                        </div>
                        <div>
                          <div>
                            {c.first_name} {c.last_name}
                          </div>
                          {c.linkedin_url && (
                            <a
                              href={c.linkedin_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[10px] text-sky-400 hover:underline flex items-center gap-1 mt-0.5"
                            >
                              <Linkedin className="w-2.5 h-2.5" />
                              <span>LinkedIn Profile</span>
                            </a>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Company */}
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-200">{comp?.name || 'Unknown'}</div>
                      {comp?.funding_amount && (
                        <span className="inline-block mt-0.5 text-[10px] font-medium px-2 py-0.5 rounded-md bg-emerald-950/70 text-emerald-400 border border-emerald-500/30">
                          {comp.funding_amount}
                        </span>
                      )}
                    </td>

                    {/* Title */}
                    <td className="py-3.5 px-4">
                      <span className="text-slate-300 font-medium">
                        {c.title || 'Engineering / Talent Lead'}
                      </span>
                    </td>

                    {/* Email */}
                    <td className="py-3.5 px-4 font-mono text-[11px] text-slate-300">
                      {c.email ? (
                        <div className="flex items-center space-x-1.5">
                          <Mail className="w-3.5 h-3.5 text-indigo-400" />
                          <span>{c.email}</span>
                        </div>
                      ) : (
                        <span className="text-slate-500 italic">No email found</span>
                      )}
                    </td>

                    {/* Stage */}
                    <td className="py-3.5 px-4">
                      <span
                        className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider border ${
                          outreach.kanban_stage === 'SENT'
                            ? 'bg-sky-950 text-sky-300 border-sky-500/40'
                            : outreach.kanban_stage === 'REPLIED'
                            ? 'bg-green-950 text-green-300 border-green-500/40'
                            : outreach.kanban_stage === 'DRAFTED'
                            ? 'bg-amber-950 text-amber-300 border-amber-500/40'
                            : outreach.kanban_stage === 'READY_TO_SEND'
                            ? 'bg-emerald-950 text-emerald-300 border-emerald-500/40'
                            : 'bg-purple-950 text-purple-300 border-purple-500/40'
                        }`}
                      >
                        {outreach.kanban_stage}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => onOpenDraftModal(outreach)}
                        className="px-3 py-1.5 rounded-xl bg-indigo-600/80 hover:bg-indigo-600 text-white font-medium text-xs transition-all shadow-sm active:scale-95 inline-flex items-center gap-1.5"
                      >
                        <Sparkles className="w-3 h-3 text-indigo-200" />
                        <span>{outreach.email_body ? 'Review Pitch' : 'Draft Pitch'}</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default ContactsDirectory;
