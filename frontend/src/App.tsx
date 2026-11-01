import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  RefreshCw,
  Cpu,
  Layers,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Building,
  Users,
  Columns,
  Send,
  MessageSquare,
  TrendingUp,
} from 'lucide-react';
import { kanbanApi, discoveryApi, enrichmentApi } from './services/api';
import type { KanbanBoard as KanbanBoardType, Outreach } from './types';
import KanbanBoard from './components/KanbanBoard';
import DiscoveryPanel from './components/DiscoveryPanel';
import ContactsDirectory from './components/ContactsDirectory';
import GmailAuthButton from './components/GmailAuthButton';
import EmailDraftModal from './components/EmailDraftModal';
import SponsorPulseLogo from './components/SponsorPulseLogo';

type ActiveTab = 'pipeline' | 'discovery' | 'contacts' | 'split';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('split');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [board, setBoard] = useState<KanbanBoardType>({
    DISCOVERED: [],
    ENRICHED: [],
    DRAFTED: [],
    READY_TO_SEND: [],
    SENT: [],
    REPLIED: [],
    CLOSED: [],
  });
  const [loadingBoard, setLoadingBoard] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);

  // Status indicators
  const [mcpOnline, setMcpOnline] = useState<boolean | null>(null);
  const [geminiOnline, setGeminiOnline] = useState<boolean | null>(null);

  // Modal state
  const [selectedOutreach, setSelectedOutreach] = useState<Outreach | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Banner notification
  const [notification, setNotification] = useState<{ message: string; type: 'info' | 'success' | 'error' } | null>(null);

  const fetchBoard = useCallback(async () => {
    try {
      const data = await kanbanApi.getKanbanBoard();
      setBoard(data);
    } catch (err) {
      console.error('Failed to load kanban board:', err);
    } finally {
      setLoadingBoard(false);
    }
  }, []);

  const checkIntegrations = useCallback(async () => {
    try {
      const mcp = await enrichmentApi.getMcpStatus();
      setMcpOnline(mcp.connected ?? true);
    } catch {
      setMcpOnline(false);
    }

    try {
      const res = await fetch('/api/health');
      setGeminiOnline(res.ok);
    } catch {
      setGeminiOnline(null);
    }
  }, []);

  useEffect(() => {
    fetchBoard();
    checkIntegrations();
  }, [fetchBoard, checkIntegrations]);

  const handleSyncFeeds = async () => {
    try {
      setIsSyncing(true);
      setNotification({ message: 'Syncing live funding feeds from TechCrunch & VentureBeat...', type: 'info' });
      const res = await discoveryApi.syncFundingFeeds();
      const count = Array.isArray(res) ? res.length : (res?.new_companies ?? 0);
      setNotification({
        message: `Sync complete! ${count > 0 ? `${count} new companies discovered.` : 'Funding feed is up to date.'}`,
        type: 'success',
      });
      setRefreshTrigger((prev) => prev + 1);
      await fetchBoard();
    } catch (err: any) {
      console.error('Failed to sync feeds:', err);
      setNotification({
        message: err.response?.data?.detail || 'Funding feed sync encountered an error.',
        type: 'error',
      });
    } finally {
      setIsSyncing(false);
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const handleOpenDraftModal = (outreach: Outreach) => {
    setSelectedOutreach(outreach);
    setIsModalOpen(true);
  };

  const handleCloseDraftModal = () => {
    setIsModalOpen(false);
    setSelectedOutreach(null);
  };

  // Pipeline metrics
  const stats = useMemo(() => {
    const discovered = board.DISCOVERED?.length || 0;
    const enriched = board.ENRICHED?.length || 0;
    const drafted = board.DRAFTED?.length || 0;
    const ready = board.READY_TO_SEND?.length || 0;
    const sent = board.SENT?.length || 0;
    const replied = board.REPLIED?.length || 0;
    const total = discovered + enriched + drafted + ready + sent + replied;
    const replyRate = (sent + replied) > 0 ? Math.round((replied / (sent + replied)) * 100) : 0;
    return { discovered, enriched, drafted, ready, sent, replied, total, replyRate };
  }, [board]);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0B0F17] text-slate-100 select-none">
      {/* Primary Top Bar */}
      <header className="h-16 px-6 border-b border-slate-800/80 bg-[#0F172A]/90 backdrop-blur-md flex items-center justify-between z-20 flex-shrink-0">
        {/* Brand with Bespoke SponsorPulse Logo */}
        <SponsorPulseLogo size="md" />

        {/* View Switcher Tabs - Clean Segmented Pill Control */}
        <nav className="hidden md:flex items-center space-x-1 bg-slate-900/90 p-1 rounded-xl border border-slate-800/80 shadow-inner">
          <button
            onClick={() => setActiveTab('pipeline')}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'pipeline'
                ? 'bg-slate-800 text-white shadow-sm border border-slate-700/70'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span>Pipeline ({stats.total})</span>
          </button>

          <button
            onClick={() => setActiveTab('discovery')}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'discovery'
                ? 'bg-slate-800 text-white shadow-sm border border-slate-700/70'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Building className="w-3.5 h-3.5 text-slate-400" />
            <span>Funding Feed</span>
          </button>

          <button
            onClick={() => setActiveTab('contacts')}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'contacts'
                ? 'bg-slate-800 text-white shadow-sm border border-slate-700/70'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Users className="w-3.5 h-3.5 text-slate-400" />
            <span>Decision-Makers</span>
          </button>

          <button
            onClick={() => setActiveTab('split')}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'split'
                ? 'bg-slate-800 text-white shadow-sm border border-slate-700/70'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
            title="Side-by-side split view"
          >
            <Columns className="w-3.5 h-3.5 text-slate-400" />
            <span>Split View</span>
          </button>
        </nav>

        {/* Status Indicators & Actions */}
        <div className="flex items-center space-x-3">
          {/* MCP & Gemini Status Badges */}
          <div className="hidden xl:flex items-center space-x-3 bg-slate-900/80 px-3 py-1.5 rounded-xl border border-slate-800 text-xs shadow-sm">
            <div className="flex items-center space-x-2" title="Enricho MCP Engine">
              <span className="relative flex h-2 w-2">
                {mcpOnline ? (
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400 shadow-sm"></span>
                ) : (
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-slate-600"></span>
                )}
              </span>
              <span className="text-slate-400 text-[11px] font-medium">MCP Engine</span>
            </div>

            <div className="w-px h-3.5 bg-slate-800" />

            <div className="flex items-center space-x-2" title="Google Gemini Flash">
              <span className="relative flex h-2 w-2">
                {geminiOnline ? (
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400 shadow-sm"></span>
                ) : (
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400"></span>
                )}
              </span>
              <span className="text-slate-400 text-[11px] font-medium">Gemini AI</span>
            </div>
          </div>

          {/* Gmail Auth Button */}
          <GmailAuthButton />

          {/* Sync Funding Feed Button */}
          <button
            onClick={handleSyncFeeds}
            disabled={isSyncing}
            className="flex items-center space-x-2 px-3.5 py-1.5 rounded-xl bg-slate-800/90 hover:bg-slate-800 active:scale-95 text-slate-100 border border-slate-700/80 hover:border-teal-500/50 text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-teal-400 ${isSyncing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">{isSyncing ? 'Syncing...' : 'Sync Funding Feed'}</span>
          </button>
        </div>
      </header>

      {/* Notification Banner */}
      {notification && (
        <div
          className={`px-5 py-2 text-xs font-medium flex items-center justify-between transition-all ${
            notification.type === 'success'
              ? 'bg-emerald-950/80 text-emerald-300 border-b border-emerald-500/20'
              : notification.type === 'error'
              ? 'bg-rose-950/80 text-rose-300 border-b border-rose-500/20'
              : 'bg-slate-900 text-teal-300 border-b border-teal-500/20'
          }`}
        >
          <div className="flex items-center space-x-2">
            {notification.type === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
            {notification.type === 'error' && <XCircle className="w-4 h-4 text-rose-400" />}
            {notification.type === 'info' && <AlertCircle className="w-4 h-4 text-teal-400" />}
            <span>{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)} className="text-xs hover:underline opacity-80">
            Dismiss
          </button>
        </div>
      )}

      {/* KPI Stats Bar - Enterprise Metric Cards */}
      {(activeTab === 'pipeline' || activeTab === 'split') && (
        <div className="px-6 py-2 bg-slate-900/40 border-b border-slate-800/80 flex items-center justify-between overflow-x-auto flex-shrink-0 text-xs gap-4">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 bg-slate-900/80 px-2.5 py-1 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[11px]">Total Pipeline:</span>
              <span className="font-bold text-slate-100">{stats.total}</span>
            </div>
            <div className="flex items-center space-x-2 bg-slate-900/80 px-2.5 py-1 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[11px]">Enriched:</span>
              <span className="font-bold text-indigo-300">{stats.enriched}</span>
            </div>
            <div className="flex items-center space-x-2 bg-slate-900/80 px-2.5 py-1 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[11px]">Drafts Ready:</span>
              <span className="font-bold text-amber-300">{stats.ready}</span>
            </div>
            <div className="flex items-center space-x-2 bg-slate-900/80 px-2.5 py-1 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[11px]">Dispatched:</span>
              <span className="font-bold text-cyan-300">{stats.sent}</span>
            </div>
            <div className="flex items-center space-x-2 bg-slate-900/80 px-2.5 py-1 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[11px]">Partner Replies:</span>
              <span className="font-bold text-emerald-400">{stats.replied}</span>
            </div>
          </div>

          <div className="flex items-center space-x-2 bg-slate-900/80 px-3 py-1 rounded-lg border border-slate-800">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-400 text-[11px]">Response Rate:</span>
            <span className="font-bold text-emerald-400">{stats.replyRate}%</span>
          </div>
        </div>
      )}

      {/* Main Workspace Display */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* VIEW 1: Dedicated Full Pipeline View */}
        {activeTab === 'pipeline' && (
          <main className="flex-1 flex flex-col h-full overflow-hidden bg-[#0B0F17]">
            <div className="flex-1 overflow-hidden">
              {loadingBoard ? (
                <div className="flex items-center justify-center h-full space-x-2 text-slate-400">
                  <RefreshCw className="w-5 h-5 animate-spin text-teal-400" />
                  <span className="text-sm">Loading outreach pipeline...</span>
                </div>
              ) : (
                <KanbanBoard
                  initialBoard={board}
                  onRefresh={fetchBoard}
                  onOpenDraftModal={handleOpenDraftModal}
                />
              )}
            </div>
          </main>
        )}

        {/* VIEW 2: Full-Width Funding Discovery Feed */}
        {activeTab === 'discovery' && (
          <main className="flex-1 flex flex-col h-full overflow-hidden bg-[#0B0F17] max-w-6xl mx-auto w-full p-4">
            <div className="flex-1 rounded-2xl overflow-hidden border border-slate-800/80 shadow-xl bg-slate-900/60 backdrop-blur-sm">
              <DiscoveryPanel onRefreshKanban={fetchBoard} refreshTrigger={refreshTrigger} />
            </div>
          </main>
        )}

        {/* VIEW 3: Corporate Directory of Identified Decision-Makers */}
        {activeTab === 'contacts' && (
          <main className="flex-1 flex flex-col h-full overflow-hidden bg-[#0B0F17]">
            <ContactsDirectory onOpenDraftModal={handleOpenDraftModal} />
          </main>
        )}

        {/* VIEW 4: Split View (Discovery Sidebar + Kanban Pipeline) */}
        {activeTab === 'split' && (
          <div className="flex-1 flex flex-col lg:flex-row h-full overflow-hidden">
            <aside className="hidden lg:flex w-96 flex-shrink-0 flex-col border-r border-slate-800/80 bg-slate-900/40">
              <DiscoveryPanel onRefreshKanban={fetchBoard} refreshTrigger={refreshTrigger} />
            </aside>
            <main className="flex-1 flex flex-col h-full overflow-hidden bg-[#0B0F17]">
              <div className="flex-1 overflow-hidden">
                <KanbanBoard
                  initialBoard={board}
                  onRefresh={fetchBoard}
                  onOpenDraftModal={handleOpenDraftModal}
                />
              </div>
            </main>
          </div>
        )}
      </div>

      {/* Mobile Bottom Navigation Bar (< 768px) */}
      <nav className="md:hidden flex items-center justify-around bg-slate-900/95 border-t border-slate-800/80 px-2 py-2 flex-shrink-0 z-30">
        <button
          onClick={() => setActiveTab('pipeline')}
          className={`flex flex-col items-center py-1 px-3 rounded-lg text-[10px] transition-colors ${
            activeTab === 'pipeline' ? 'text-teal-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4 mb-0.5" />
          <span>Pipeline</span>
        </button>

        <button
          onClick={() => setActiveTab('discovery')}
          className={`flex flex-col items-center py-1 px-3 rounded-lg text-[10px] transition-colors ${
            activeTab === 'discovery' ? 'text-teal-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Building className="w-4 h-4 mb-0.5" />
          <span>Feed</span>
        </button>

        <button
          onClick={() => setActiveTab('contacts')}
          className={`flex flex-col items-center py-1 px-3 rounded-lg text-[10px] transition-colors ${
            activeTab === 'contacts' ? 'text-teal-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users className="w-4 h-4 mb-0.5" />
          <span>Directory</span>
        </button>

        <button
          onClick={() => setActiveTab('split')}
          className={`flex flex-col items-center py-1 px-3 rounded-lg text-[10px] transition-colors ${
            activeTab === 'split' ? 'text-teal-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Columns className="w-4 h-4 mb-0.5" />
          <span>Split</span>
        </button>
      </nav>

      {/* Email Draft / Review Modal */}
      <EmailDraftModal
        outreach={selectedOutreach}
        isOpen={isModalOpen}
        onClose={handleCloseDraftModal}
        onRefresh={fetchBoard}
      />
    </div>
  );
};

export default App;
