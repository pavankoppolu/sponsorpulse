import React, { useState, useEffect, useRef } from 'react';
import {
  Mail,
  CheckCircle2,
  Loader2,
  ExternalLink,
  HelpCircle,
  X,
  FileCode,
  Sparkles,
  LogOut,
  AlertTriangle,
} from 'lucide-react';
import { authApi } from '../services/api';
import type { GmailAuthStatus } from '../types';

interface GmailAuthButtonProps {
  onStatusChange?: (status: GmailAuthStatus) => void;
}

export const GmailAuthButton: React.FC<GmailAuthButtonProps> = ({ onStatusChange }) => {
  const [status, setStatus] = useState<GmailAuthStatus>({ authenticated: false, email: null });
  const [loading, setLoading] = useState<boolean>(true);
  const [isAuthenticating, setIsAuthenticating] = useState<boolean>(false);
  const [showSetupModal, setShowSetupModal] = useState<boolean>(false);
  const [connectingDev, setConnectingDev] = useState<boolean>(false);

  const authWindowRef = useRef<Window | null>(null);
  const pollTimerRef = useRef<number | null>(null);

  const fetchStatus = async () => {
    try {
      const data = await authApi.getGmailStatus();
      setStatus(data);
      if (onStatusChange) {
        onStatusChange(data);
      }
      return data;
    } catch (err) {
      console.error('Failed to get Gmail auth status:', err);
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, []);

  const stopPolling = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    setIsAuthenticating(false);
    authWindowRef.current = null;
  };

  const startPolling = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
    }

    pollTimerRef.current = window.setInterval(async () => {
      if (authWindowRef.current && authWindowRef.current.closed) {
        stopPolling();
        await fetchStatus();
        return;
      }

      const res = await fetchStatus();
      if (res && res.authenticated) {
        if (authWindowRef.current && !authWindowRef.current.closed) {
          authWindowRef.current.close();
        }
        stopPolling();
      }
    }, 2500);
  };

  const handleConnectClick = async () => {
    try {
      setIsAuthenticating(true);

      // Check if credentials.json is configured on the backend
      const cfg = await authApi.getConfigStatus();

      if (!cfg.credentials_present) {
        // Show setup modal with guide & 1-click dev connect
        setIsAuthenticating(false);
        setShowSetupModal(true);
        return;
      }

      // If credentials.json exists, launch real Google OAuth popup
      const res = await authApi.getGmailAuthUrl();
      const url = res.url || res.auth_url;

      if (!url) {
        alert('Could not retrieve authentication URL.');
        setIsAuthenticating(false);
        return;
      }

      const width = 550;
      const height = 650;
      const left = window.screen.width / 2 - width / 2;
      const top = window.screen.height / 2 - height / 2;

      authWindowRef.current = window.open(
        url,
        'GmailOAuth',
        `width=${width},height=${height},top=${top},left=${left},toolbar=no,menubar=no,scrollbars=yes,resizable=yes`
      );

      startPolling();
    } catch (err: any) {
      console.error('Error initiating Gmail auth:', err);
      const detail = err?.response?.data?.detail;
      // If credentials missing, show setup modal instead of harsh alert
      if (detail && detail.includes('credentials.json')) {
        setShowSetupModal(true);
      } else {
        alert(detail || 'Failed to initiate Gmail authorization. Please check backend configuration.');
      }
      setIsAuthenticating(false);
    }
  };

  const handleDevConnect = async () => {
    try {
      setConnectingDev(true);
      await authApi.devConnectGmail('outreach@sponsorpulse.local');
      await fetchStatus();
      setShowSetupModal(false);
    } catch (err) {
      console.error('Dev connect error:', err);
      alert('Failed to connect development account.');
    } finally {
      setConnectingDev(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Disconnect this Gmail account from SponsorPulse?')) return;
    try {
      await authApi.revokeGmail();
      await fetchStatus();
    } catch (err) {
      console.error('Revoke error:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-slate-800 text-slate-400 text-xs font-medium border border-slate-700">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        <span>Checking Gmail...</span>
      </div>
    );
  }

  return (
    <>
      {status.authenticated ? (
        <div className="flex items-center space-x-2 bg-emerald-950/70 border border-emerald-500/30 text-emerald-300 text-xs font-medium rounded-xl px-3 py-1.5 shadow-sm">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <Mail className="w-3.5 h-3.5 text-emerald-400" />
          <span className="max-w-[160px] truncate" title={status.email || 'Connected'}>
            {status.email ? status.email : 'Gmail Active'}
          </span>
          <button
            onClick={handleDisconnect}
            className="ml-1 text-slate-400 hover:text-rose-400 transition-colors p-0.5 rounded"
            title="Disconnect account"
          >
            <LogOut className="w-3 h-3" />
          </button>
        </div>
      ) : (
        <button
          onClick={handleConnectClick}
          disabled={isAuthenticating}
          className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all shadow-sm ${
            isAuthenticating
              ? 'bg-amber-950/70 text-amber-300 border border-amber-600/40 cursor-wait'
              : 'bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500/80 shadow-indigo-900/30 active:scale-95'
          }`}
        >
          {isAuthenticating ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />
              <span>Connecting...</span>
            </>
          ) : (
            <>
              <Mail className="w-3.5 h-3.5" />
              <span>Connect Gmail</span>
              <ExternalLink className="w-3 h-3 opacity-70" />
            </>
          )}
        </button>
      )}

      {/* Gmail OAuth Setup & Instant Dev Connect Modal */}
      {showSetupModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150 overflow-y-auto">
          <div className="relative my-auto w-full max-w-lg max-h-[90vh] flex flex-col bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden text-slate-100">
            {/* Modal Header */}
            <div className="px-5 sm:px-6 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-900/90 flex-shrink-0">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-400">
                  <Mail className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Gmail Integration Setup</h3>
                  <p className="text-[11px] text-slate-400">Connect Google account or use 1-click Test Mode</p>
                </div>
              </div>
              <button
                onClick={() => setShowSetupModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                title="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body with dedicated scroll */}
            <div className="p-4 sm:p-6 space-y-4 text-xs text-slate-300 flex-1 overflow-y-auto custom-scrollbar">
              {/* Notice Banner */}
              <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-500/30 flex items-start space-x-2.5 text-amber-200/90">
                <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <p className="font-semibold text-amber-200 text-xs">Credentials Configuration</p>
                  <p className="text-[11px] leading-relaxed text-amber-300/80">
                    To send live emails to real inboxes, Google requires an OAuth credentials file. For development or rapid demo, use Option 1 below.
                  </p>
                </div>
              </div>

              {/* Option 1: Instant Dev / Test Mode */}
              <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/80 space-y-2.5 shadow-sm">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-teal-400" />
                    <span className="font-bold text-slate-100 text-xs">Option 1: Instant 1-Click Test Mode</span>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-teal-950 text-teal-300 border border-teal-700/50 text-[10px] font-semibold whitespace-nowrap">
                    Instant Demo
                  </span>
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Enables simulated email dispatch and automated thread tracking. Lets you test the full pipeline, Gemini drafting, and Kanban stages immediately without setting up a Google Cloud project.
                </p>
                <button
                  onClick={handleDevConnect}
                  disabled={connectingDev}
                  className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white font-semibold text-xs transition-all shadow-sm flex items-center justify-center space-x-2 disabled:opacity-50 active:scale-98"
                >
                  {connectingDev ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Connecting Test Account...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Connect Test Account (outreach@sponsorpulse.local)</span>
                    </>
                  )}
                </button>
              </div>

              {/* Option 2: Real Google Cloud OAuth Setup */}
              <div className="p-4 rounded-xl bg-slate-800/30 border border-slate-700/50 space-y-2.5">
                <div className="flex items-center space-x-2">
                  <FileCode className="w-4 h-4 text-slate-400" />
                  <span className="font-bold text-slate-100 text-xs">Option 2: Real Google Account Setup</span>
                </div>
                <ol className="list-decimal list-inside space-y-1 text-slate-400 text-[11px] leading-relaxed">
                  <li>
                    Go to <a href="https://console.cloud.google.com" target="_blank" rel="noreferrer" className="text-teal-400 underline">Google Cloud Console</a>.
                  </li>
                  <li>Enable the <strong>Gmail API</strong> under APIs &amp; Services.</li>
                  <li>Create Credentials &rarr; <strong>OAuth client ID</strong> &rarr; <strong>Desktop app</strong>.</li>
                  <li>Save credentials JSON file as:</li>
                </ol>
                <div className="p-2 rounded-lg bg-slate-950 font-mono text-[10px] text-teal-400 select-all border border-slate-800 break-all">
                  C:\Users\pavan\sponsorpulse\backend\credentials\credentials.json
                </div>
                <div className="flex justify-end pt-1">
                  <button
                    onClick={handleConnectClick}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
                  >
                    I placed the file, retry Google Login
                  </button>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-5 sm:px-6 py-3 border-t border-slate-800 bg-slate-900/60 flex justify-end flex-shrink-0">
              <button
                onClick={() => setShowSetupModal(false)}
                className="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 font-medium text-xs transition-colors border border-slate-700/70"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default GmailAuthButton;
