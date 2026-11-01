import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  DollarSign,
  Calendar,
  ExternalLink,
  PlusCircle,
  Loader2,
  Building,
  Filter,
  CheckCircle,
  Sparkles,
} from 'lucide-react';
import type { Company } from '../types';
import { discoveryApi, enrichmentApi } from '../services/api';

interface DiscoveryPanelProps {
  onRefreshKanban: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  refreshTrigger?: number;
}

export const DiscoveryPanel: React.FC<DiscoveryPanelProps> = ({
  onRefreshKanban,
  refreshTrigger,
}) => {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [enrichingIds, setEnrichingIds] = useState<Set<number>>(new Set());
  const [enrichedIds, setEnrichedIds] = useState<Set<number>>(new Set());

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [minFunding, setMinFunding] = useState('');
  const [dateFilter, setDateFilter] = useState('');

  const fetchCompanies = async () => {
    try {
      setLoading(true);
      const data = await discoveryApi.getCompanies({
        search: searchTerm || undefined,
        min_funding: minFunding || undefined,
        date_from: dateFilter || undefined,
      });
      setCompanies(data);
    } catch (err) {
      console.error('Failed to load discovered companies:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCompanies();
  }, [dateFilter, refreshTrigger]);

  // Debounced search on enter or when search fields update
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchCompanies();
  };

  const handleEnrichAndAdd = async (company: Company) => {
    try {
      setEnrichingIds((prev) => new Set(prev).add(company.id));
      await enrichmentApi.enrichCompany(company.id);
      setEnrichedIds((prev) => new Set(prev).add(company.id));
      onRefreshKanban();
    } catch (err: any) {
      console.error('Failed to enrich company:', err);
      alert(err.response?.data?.detail || 'Failed to enrich company. Ensure MCP server is active.');
    } finally {
      setEnrichingIds((prev) => {
        const next = new Set(prev);
        next.delete(company.id);
        return next;
      });
    }
  };

  const filteredCompanies = useMemo(() => {
    return companies.filter((c) => {
      if (searchTerm) {
        const matchName = c.name.toLowerCase().includes(searchTerm.toLowerCase());
        const matchDomain = c.domain?.toLowerCase().includes(searchTerm.toLowerCase());
        const matchSummary = c.summary?.toLowerCase().includes(searchTerm.toLowerCase());
        if (!matchName && !matchDomain && !matchSummary) return false;
      }
      if (minFunding && c.funding_amount) {
        if (!c.funding_amount.toLowerCase().includes(minFunding.toLowerCase())) {
          return false;
        }
      }
      return true;
    });
  }, [companies, searchTerm, minFunding]);

  return (
    <div className="flex flex-col h-full bg-slate-950/60 border-r border-slate-800/80">
      {/* Panel Header */}
      <div className="p-4 border-b border-slate-800/80 bg-slate-900/70">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400">
              <Building className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-semibold text-slate-100">Funding Discovery</h2>
          </div>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/60">
            {filteredCompanies.length} found
          </span>
        </div>
        <p className="text-xs text-slate-400">Recently funded companies from live feeds</p>

        {/* Filter Bar */}
        <form onSubmit={handleSearchSubmit} className="mt-3 space-y-2">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search companies or domain..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/80 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-teal-500/50"
            />
          </div>

          {/* Sub Filters: Min funding & Date */}
          <div className="grid grid-cols-2 gap-2">
            <div className="relative">
              <DollarSign className="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-500" />
              <input
                type="text"
                placeholder="Min Funding (e.g. $5M)"
                value={minFunding}
                onChange={(e) => setMinFunding(e.target.value)}
                className="w-full pl-7 pr-2 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/80 text-[11px] text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-teal-500/50"
              />
            </div>
            <div className="relative">
              <Calendar className="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-500" />
              <input
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="w-full pl-7 pr-2 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/80 text-[11px] text-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500/50"
              />
            </div>
          </div>
        </form>
      </div>

      {/* Companies List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5 custom-scrollbar">
        {loading ? (
          /* Loading Skeletons */
          Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="p-3.5 rounded-xl bg-slate-900/40 border border-slate-800 animate-pulse space-y-2.5"
            >
              <div className="flex justify-between items-center">
                <div className="h-4 bg-slate-800 rounded w-1/2"></div>
                <div className="h-4 bg-slate-800 rounded-full w-16"></div>
              </div>
              <div className="h-3 bg-slate-800/60 rounded w-3/4"></div>
              <div className="h-7 bg-slate-800/50 rounded-lg w-full mt-2"></div>
            </div>
          ))
        ) : filteredCompanies.length === 0 ? (
          /* Empty State */
          <div className="h-64 flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl">
            <Filter className="w-7 h-7 text-slate-600 mb-2" />
            <h4 className="text-xs font-semibold text-slate-400">No companies found</h4>
            <p className="text-[11px] text-slate-500 mt-1 max-w-[200px]">
              Click "Sync Funding Feed" at the top to fetch the latest announcements or adjust filters.
            </p>
          </div>
        ) : (
          filteredCompanies.map((company) => {
            const isEnriching = enrichingIds.has(company.id);
            const isEnriched = enrichedIds.has(company.id);

            return (
              <div
                key={company.id}
                className="p-3.5 rounded-xl bg-slate-900/60 hover:bg-slate-900 border border-slate-800/80 hover:border-slate-700/80 shadow-sm transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-xs font-semibold text-slate-100 truncate" title={company.name}>
                      {company.name}
                    </h3>
                    {company.funding_amount && (
                      <span className="flex-shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {company.funding_amount}
                      </span>
                    )}
                  </div>

                  {company.domain && (
                    <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                      {company.domain}
                    </div>
                  )}

                  {company.summary && (
                    <p className="text-[11px] text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                      {company.summary}
                    </p>
                  )}

                  <div className="flex items-center justify-between text-[10px] text-slate-500 mt-2.5 pt-2 border-t border-slate-800/60">
                    <span>
                      {company.funding_date
                        ? new Date(company.funding_date).toLocaleDateString()
                        : new Date(company.created_at).toLocaleDateString()}
                    </span>
                    {company.source_url && (
                      <a
                        href={company.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center space-x-1 text-teal-400 hover:text-teal-300 hover:underline"
                      >
                        <span>Source</span>
                        <ExternalLink className="w-2.5 h-2.5" />
                      </a>
                    )}
                  </div>
                </div>

                <div className="mt-3">
                  <button
                    onClick={() => handleEnrichAndAdd(company)}
                    disabled={isEnriching || isEnriched}
                    className={`w-full py-1.5 px-3 rounded-lg text-xs font-medium flex items-center justify-center space-x-1.5 transition-all shadow-sm ${
                      isEnriched
                        ? 'bg-slate-800/80 text-emerald-400 border border-emerald-500/30 cursor-default'
                        : 'bg-slate-800 hover:bg-slate-750 text-teal-300 border border-teal-500/30 hover:border-teal-500/50 active:scale-98'
                    }`}
                  >
                    {isEnriching ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-400" />
                        <span>Enriching via MCP...</span>
                      </>
                    ) : isEnriched ? (
                      <>
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Added to Pipeline</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5 text-teal-400" />
                        <span>Enrich & Add to Pipeline</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default DiscoveryPanel;
