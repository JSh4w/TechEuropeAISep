export const dynamic = "force-dynamic";

export async function GET() {
  const isAuthExplicitlyDisabled = process.env.AUTH_ENABLED === "false";
  const hasFirebaseConfig = Boolean(
    process.env.FIREBASE_PROJECT_ID &&
    process.env.FIREBASE_API_KEY &&
    process.env.FIREBASE_AUTH_DOMAIN &&
    process.env.FIREBASE_APP_ID
  );
  const authEnabled = !isAuthExplicitlyDisabled && (process.env.AUTH_ENABLED === "true" || hasFirebaseConfig);

  return Response.json({
    authEnabled,
    firebase: {
      apiKey: process.env.FIREBASE_API_KEY || null,
      authDomain: process.env.FIREBASE_AUTH_DOMAIN || null,
      projectId: process.env.FIREBASE_PROJECT_ID || null,
      appId: process.env.FIREBASE_APP_ID || null,
    },
  });
}
