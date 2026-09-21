import { getApp, getApps, initializeApp, type FirebaseApp } from 'firebase/app';
import { getAuth, type Auth } from 'firebase/auth';

const config = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

// Without Firebase config the app runs in local mode: no sign-in, no bearer token (the local API has no auth).
export const authEnabled = Boolean(config.apiKey && config.authDomain && config.projectId && config.appId);

let app: FirebaseApp | null = null;

export function firebaseAuth(): Auth {
  if (!authEnabled) throw new Error('Firebase is not configured');
  app ??= getApps().length ? getApp() : initializeApp(config);
  return getAuth(app);
}
