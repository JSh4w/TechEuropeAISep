import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

export const dynamic = "force-dynamic";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Bessible — BESS Site Assessor & Feasibility Engine",
  description: "Autonomous grid screening, footprint sizing, and explainable battery energy storage feasibility.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const isAuthExplicitlyDisabled = process.env.AUTH_ENABLED === "false";
  const hasFirebaseConfig = Boolean(
    process.env.FIREBASE_PROJECT_ID &&
    process.env.FIREBASE_API_KEY &&
    process.env.FIREBASE_AUTH_DOMAIN &&
    process.env.FIREBASE_APP_ID
  );
  const authEnabled = !isAuthExplicitlyDisabled && (process.env.AUTH_ENABLED === "true" || hasFirebaseConfig);

  const runtimeConfig = {
    enabled: authEnabled,
    firebase: {
      apiKey: process.env.FIREBASE_API_KEY || "",
      authDomain: process.env.FIREBASE_AUTH_DOMAIN || "",
      projectId: process.env.FIREBASE_PROJECT_ID || "",
      appId: process.env.FIREBASE_APP_ID || "",
    },
    googleMaps: {
      apiKey: process.env.GOOGLE_MAPS_API_KEY || "",
      mapId: process.env.GOOGLE_MAPS_MAP_ID || "",
    },
  };

  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script
          id="runtime-config"
          dangerouslySetInnerHTML={{
            __html: `window.__CONFIG__ = ${JSON.stringify(runtimeConfig)};`,
          }}
        />
      </head>
      <body className="min-h-full flex flex-col">
        <AuthProvider config={runtimeConfig}>{children}</AuthProvider>
      </body>
    </html>
  );
}
