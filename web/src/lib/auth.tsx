'use client';

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
  type User,
} from 'firebase/auth';
import { authEnabled, firebaseAuth } from './firebase';
import { setTokenGetter } from './api';

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
if (authEnabled) {
  setTokenGetter(async () => firebaseAuth().currentUser?.getIdToken() ?? null);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [firebaseUser, setFirebaseUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(authEnabled);

  useEffect(() => {
    if (!authEnabled) return;
    return onAuthStateChanged(firebaseAuth(), (u) => {
      setFirebaseUser(u);
      setLoading(false);
    });
  }, []);

  const signIn = useCallback(async () => {
    await signInWithPopup(firebaseAuth(), new GoogleAuthProvider());
  }, []);

  const signOut = useCallback(async () => {
    await firebaseSignOut(firebaseAuth());
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      enabled: authEnabled,
      loading,
      user: firebaseUser
        ? { uid: firebaseUser.uid, email: firebaseUser.email, name: firebaseUser.displayName }
        : null,
      signIn,
      signOut,
    }),
    [firebaseUser, loading, signIn, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
