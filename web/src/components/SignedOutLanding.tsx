'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { LogIn, PlayCircle } from 'lucide-react';

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
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 -960 960 960"
            width="32"
            height="32"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M320-80q-17 0-28.5-11.5T280-120v-640q0-17 11.5-28.5T320-800h80v-80h160v80h80q17 0 28.5 11.5T680-760v280q-100 1-170 70.5T440-240q0 46 16 87t45 73H320Zm40-400h240v-240H360v240ZM660-80v-120H560l140-200v120h100L660-80Z" />
          </svg>
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
