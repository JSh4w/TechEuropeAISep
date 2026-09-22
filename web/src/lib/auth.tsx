'use client';

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
  type User,
} from 'firebase/auth';
import { authEnabled as initialAuthEnabled, firebaseAuth, initFirebase, type FirebaseClientConfig } from './firebase';
import { setTokenGetter } from './api';

export interface RuntimeConfig {
  enabled: boolean;
  firebase?: FirebaseClientConfig;
}

interface AuthState {
  /** False in local mode (no Firebase config): everything is open and no token is sent. */
  enabled: boolean;
  /** True until Firebase reports the initial session. */
  loading: boolean;
  user: { uid: string; email: string | null; name: string | null } | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

// Registered at module load (not in an effect) so child effects never call the API before it exists.
// getIdToken() returns the cached token and refreshes it when it is close to expiry.
if (initialAuthEnabled) {
  setTokenGetter(async () => {
    try {
      return (await firebaseAuth().currentUser?.getIdToken()) ?? null;
    } catch {
      return null;
    }
  });
}

export function AuthProvider({
  children,
  config,
}: {
  children: React.ReactNode;
  config?: RuntimeConfig;
}) {
  const isEnabled = config
    ? config.enabled &&
      Boolean(
        config.firebase?.apiKey &&
        config.firebase?.authDomain &&
        config.firebase?.projectId &&
        config.firebase?.appId
      )
    : initialAuthEnabled;

  if (isEnabled && config?.firebase) {
    initFirebase(config.firebase);
    setTokenGetter(async () => {
      try {
        return (await firebaseAuth().currentUser?.getIdToken()) ?? null;
      } catch {
        return null;
      }
    });
  }

  const [firebaseUser, setFirebaseUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(isEnabled);

  useEffect(() => {
    if (!isEnabled) return;
    return onAuthStateChanged(firebaseAuth(), (u) => {
      setFirebaseUser(u);
      setLoading(false);
    });
  }, [isEnabled]);

  const signIn = useCallback(async () => {
    await signInWithPopup(firebaseAuth(), new GoogleAuthProvider());
  }, []);

  const signOut = useCallback(async () => {
    await firebaseSignOut(firebaseAuth());
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      enabled: isEnabled,
      loading,
      user: firebaseUser
        ? { uid: firebaseUser.uid, email: firebaseUser.email, name: firebaseUser.displayName }
        : null,
      signIn,
      signOut,
    }),
    [firebaseUser, isEnabled, loading, signIn, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
