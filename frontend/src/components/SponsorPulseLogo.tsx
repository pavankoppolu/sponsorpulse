import React from 'react';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  showSubtitle?: boolean;
  className?: string;
}

export const SponsorPulseLogo: React.FC<LogoProps> = ({
  size = 'md',
  showText = true,
  showSubtitle = true,
  className = '',
}) => {
  const dimensions = {
    sm: { box: 'w-7 h-7', icon: 28, text: 'text-sm', sub: 'text-[10px]' },
    md: { box: 'w-9 h-9', icon: 36, text: 'text-base', sub: 'text-[11px]' },
    lg: { box: 'w-11 h-11', icon: 44, text: 'text-lg', sub: 'text-xs' },
  }[size];

  return (
    <div className={`flex items-center space-x-3 select-none ${className}`}>
      {/* Precision Geometric SVG Emblem */}
      <div
        className={`${dimensions.box} rounded-xl bg-slate-900 border border-slate-700/80 shadow-sm flex items-center justify-center p-1.5 transition-transform hover:scale-105`}
      >
        <svg viewBox="0 0 40 40" fill="none" className="w-full h-full">
          <defs>
            <linearGradient id="logo-grad" x1="4" y1="20" x2="36" y2="20" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#0EA5E9" />
              <stop offset="50%" stopColor="#10B981" />
              <stop offset="100%" stopColor="#6366F1" />
            </linearGradient>
            <filter id="logo-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="1" stdDeviation="1.5" floodColor="#0EA5E9" floodOpacity="0.4" />
            </filter>
          </defs>

          {/* Geometric Pulse Waveform */}
          <path
            d="M6 21 H12 L16 11 L22 30 L27 16 L30 21 H35"
            stroke="url(#logo-grad)"
            strokeWidth="3.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            filter="url(#logo-glow)"
          />

          {/* Crest node */}
          <circle cx="16" cy="11" r="2.2" fill="#FFFFFF" />
          {/* Target engagement node */}
          <circle cx="35" cy="21" r="1.8" fill="#6366F1" />
        </svg>
      </div>

      {/* Brand Text */}
      {showText && (
        <div className="flex flex-col">
          <div className="flex items-center space-x-1.5 leading-none">
            <span className="font-bold text-slate-100 tracking-tight">Sponsor</span>
            <span className="font-extrabold bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">
              Pulse
            </span>
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 ml-1">
              v1.2
            </span>
          </div>
          {showSubtitle && (
            <span className="hidden sm:inline text-[11px] font-medium text-slate-400 tracking-normal mt-0.5">
              Talent & Corporate Outreach
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default SponsorPulseLogo;
