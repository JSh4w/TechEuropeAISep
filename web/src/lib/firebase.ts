import { getApp, getApps, initializeApp, type FirebaseApp } from 'firebase/app';
import { getAuth, type Auth } from 'firebase/auth';

export interface FirebaseClientConfig {
  apiKey?: string;
  authDomain?: string;
  projectId?: string;
  appId?: string;
}

let app: FirebaseApp | null = null;

function getRuntimeConfig(): { enabled: boolean; firebase: FirebaseClientConfig } {
  if (typeof window !== 'undefined' && (window as unknown as { __CONFIG__?: { enabled: boolean; firebase: FirebaseClientConfig } }).__CONFIG__) {
    return (window as unknown as { __CONFIG__: { enabled: boolean; firebase: FirebaseClientConfig } }).__CONFIG__;
  }
  const isAuthExplicitlyDisabled = process.env.AUTH_ENABLED === 'false';
  const hasFirebaseConfig = Boolean(
    process.env.FIREBASE_PROJECT_ID &&
    process.env.FIREBASE_API_KEY &&
    process.env.FIREBASE_AUTH_DOMAIN &&
    process.env.FIREBASE_APP_ID
  );
  const enabled = !isAuthExplicitlyDisabled && (process.env.AUTH_ENABLED === 'true' || hasFirebaseConfig);

  return {
    enabled,
    firebase: {
      apiKey: process.env.FIREBASE_API_KEY,
      authDomain: process.env.FIREBASE_AUTH_DOMAIN,
      projectId: process.env.FIREBASE_PROJECT_ID,
      appId: process.env.FIREBASE_APP_ID,
    },
  };
}

const initial = getRuntimeConfig();
export let authEnabled = initial.enabled && Boolean(
  initial.firebase.apiKey &&
  initial.firebase.authDomain &&
  initial.firebase.projectId &&
  initial.firebase.appId
);

export function initFirebase(config?: FirebaseClientConfig | null): Auth | null {
  const cfg = config || getRuntimeConfig().firebase;
  if (!cfg.apiKey || !cfg.authDomain || !cfg.projectId || !cfg.appId) {
    authEnabled = false;
    return null;
  }
  authEnabled = true;
  if (!getApps().length) {
    app = initializeApp(cfg);
  } else {
    app = getApp();
  }
  return getAuth(app);
}

// Initialize on module load if config is already present
if (authEnabled) {
  try {
    initFirebase(initial.firebase);
  } catch {
    // Graceful fallback if initialization fails
  }
}

export function firebaseAuth(): Auth {
  if (app) return getAuth(app);
  if (getApps().length) {
    app = getApp();
    return getAuth(app);
  }
  const cfg = getRuntimeConfig().firebase;
  if (cfg.apiKey && cfg.projectId) {
    app = initializeApp(cfg);
    return getAuth(app);
  }
  throw new Error('Firebase is not configured');
}
