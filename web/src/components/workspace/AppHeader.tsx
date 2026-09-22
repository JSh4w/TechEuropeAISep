'use client';

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RotateCcw } from 'lucide-react';

export function BessibleLogo({ size = 20 }: { size?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 -960 960 960"
      width={size}
      height={size}
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M320-80q-17 0-28.5-11.5T280-120v-640q0-17 11.5-28.5T320-800h80v-80h160v80h80q17 0 28.5 11.5T680-760v280q-100 1-170 70.5T440-240q0 46 16 87t45 73H320Zm40-400h240v-240H360v240ZM660-80v-120H560l140-200v120h100L660-80Z" />
    </svg>
  );
}

interface AppHeaderProps {
  onHome: () => void;
  runId: string | null;
  onResetRun: () => void;
  /** Mode-specific controls (badges, sign-in, settings), shown before the reset button. */
  children?: React.ReactNode;
}

export default function AppHeader({ onHome, runId, onResetRun, children }: AppHeaderProps) {
  return (
    <header className="bg-card/90 backdrop-blur-md border-b border-border/80 px-6 py-3.5 flex items-center justify-between shadow-xs sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onHome}
          aria-label="Back to start"
          title="Back to start"
          className="bg-emerald-600 text-white p-2.5 rounded-xl shadow-xs hover:bg-emerald-500 transition-colors cursor-pointer"
        >
          <BessibleLogo />
        </button>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold tracking-tight">Bessible</span>
            <Badge variant="outline" className="text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30">
              BESS Screening Terminal
            </Badge>
          </div>
          <p className="text-[11px] text-muted-foreground hidden sm:block">
            Autonomous grid screening, footprint sizing & explainable investment feasibility
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden md:flex items-center gap-2 text-[11px] font-mono text-muted-foreground border-r border-border pr-3">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-700 dark:text-blue-300 font-semibold border border-blue-500/20">
            Temporal Engine
          </span>
        </div>

        {children}

        {runId && (
          <Button
            variant="outline"
            size="sm"
            onClick={onResetRun}
            className="gap-1.5 text-xs h-8 px-3 rounded-xl border-border cursor-pointer hover:bg-muted/80 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Run</span>
          </Button>
        )}
      </div>
    </header>
  );
}
