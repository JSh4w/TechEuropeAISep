'use client';

import React, { useState, useSyncExternalStore } from 'react';
import SignedOutLanding from '../components/SignedOutLanding';
import DemoWorkspace, { DemoPreview } from '../components/workspace/DemoWorkspace';
import LiveWorkspace from '../components/workspace/LiveWorkspace';
import { BessibleLogo } from '../components/workspace/AppHeader';
import { useAuth } from '../lib/auth';

const noSubscribe = () => () => {};

export default function Home() {
  const auth = useAuth();
  // ?state=demo opens the demo; ?state=confirm|report open a fixed demo state for UI checks.
  // The URL decides until the visitor picks a mode themselves.
  const search = useSyncExternalStore(noSubscribe, () => window.location.search, () => '');
  const urlState = new URLSearchParams(search).get('state');
  const urlPreview: DemoPreview | null = urlState === 'confirm' || urlState === 'report' ? urlState : null;
  const [demoChoice, setDemo] = useState<boolean | null>(null);
  const demo = demoChoice ?? (urlState === 'demo' || urlPreview !== null);
  const preview = demoChoice === null ? urlPreview : null;
  const [welcomeDismissed, setWelcomeDismissed] = useState(false);
  const [signingIn, setSigningIn] = useState(false);
  const [signInError, setSignInError] = useState<string | null>(null);

  const handleSignIn = async () => {
    setSigningIn(true);
    setSignInError(null);
    try {
      await auth.signIn();
      setDemo(false); // a fresh live workspace for the new session
    } catch (err) {
      const code = (err as { code?: string })?.code;
      if (code !== 'auth/popup-closed-by-user' && code !== 'auth/cancelled-popup-request') {
        setSignInError('Sign-in failed. Try again.');
      }
    } finally {
      setSigningIn(false);
    }
  };

  const viewDemo = () => {
    setWelcomeDismissed(true);
    setDemo(true);
  };

  if (auth.enabled && auth.loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <div className="flex flex-col items-center gap-3">
          <div className="bg-emerald-600 text-white p-3.5 rounded-2xl shadow-xs animate-pulse">
            <BessibleLogo size={32} />
          </div>
          <span className="text-xs text-muted-foreground font-medium animate-pulse">Loading Bessible…</span>
        </div>
      </div>
    );
  }

  const signedOut = auth.enabled && !auth.user;

  if (demo) {
    return (
      <DemoWorkspace
        preview={preview}
        onExit={() => setDemo(false)}
        onSignIn={signedOut ? handleSignIn : undefined}
        signingIn={signingIn}
      />
    );
  }

  if (signedOut) {
    return (
      <SignedOutLanding onSignIn={handleSignIn} onViewDemo={viewDemo} signingIn={signingIn} error={signInError} />
    );
  }

  return (
    <LiveWorkspace
      key={auth.user?.uid ?? 'local'}
      onViewDemo={viewDemo}
      welcomeDismissed={welcomeDismissed}
      onDismissWelcome={() => setWelcomeDismissed(true)}
    />
  );
}
