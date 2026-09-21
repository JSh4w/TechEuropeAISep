'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { BatteryCharging, LogIn, PlayCircle } from 'lucide-react';

interface SignedOutLandingProps {
  onSignIn: () => void;
  onViewDemo: () => void;
  signingIn?: boolean;
  error?: string | null;
}

/** What a visitor with no session sees. Final copy and layout to be decided later. */
export default function SignedOutLanding({ onSignIn, onViewDemo, signingIn, error }: SignedOutLandingProps) {
  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="mx-auto w-fit bg-emerald-600 text-white p-3.5 rounded-2xl shadow-xs">
          <BatteryCharging className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h1 className="text-2xl font-bold tracking-tight">Bessible</h1>
          <p className="text-sm text-muted-foreground">
            Autonomous grid screening, footprint sizing and explainable feasibility for battery energy storage sites.
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <Button
            type="button"
            onClick={onSignIn}
            disabled={signingIn}
            className="bg-emerald-600 hover:bg-emerald-500 text-white h-11 gap-2"
          >
            <LogIn className="w-4 h-4" />
            {signingIn ? 'Signing in…' : 'Sign in with Google'}
          </Button>
          <Button type="button" variant="outline" onClick={onViewDemo} className="h-11 gap-2">
            <PlayCircle className="w-4 h-4" />
            View demo run
          </Button>
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
    </div>
  );
}
