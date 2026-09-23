'use client';

import React, { useEffect, useRef, useState } from 'react';
import KeyPanel from '../KeyPanel';
import FirstLoadModal from '../FirstLoadModal';
import AppHeader from './AppHeader';
import PostcodeInput from './PostcodeInput';
import RunView from './RunView';
import { Button } from '@/components/ui/button';
import { LogOut, Search, Settings } from 'lucide-react';
import { AssessmentRequest, SiteData } from '../../lib/types';
import { ApiError, KeyStatus, checkCapacity, getKeyStatus, getSiteData, startRun } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { distanceKm } from '../../lib/footprint';
import { geocodePostcode, nearestPostcode } from '../../lib/geocode';
import { CapacityChecker, DEFAULT_CENTER, useSiteRun } from '../../lib/useSiteRun';

const checkLiveCapacity: CapacityChecker = (pos, flexible) => checkCapacity(pos, flexible).catch(() => null);

/** Real data for wherever the pin is: coordinate -> location.collate -> LocationData. */
function useSiteData([lon, lat]: [number, number]) {
  const [siteData, setSiteData] = useState<SiteData | null>(null);
  const [siteDataLoading, setSiteDataLoading] = useState(false);

  useEffect(() => {
    if (lon === DEFAULT_CENTER[0] && lat === DEFAULT_CENTER[1]) return; // untouched default
    let stale = false;
    const timer = setTimeout(async () => {
      setSiteDataLoading(true);
      try {
        const data = await getSiteData(lat, lon);
        if (!stale && data) setSiteData(data);
      } catch {
        // keep the last layer
      } finally {
        if (!stale) setSiteDataLoading(false);
      }
    }, 400);
    return () => {
      stale = true;
      clearTimeout(timer);
    };
  }, [lon, lat]);

  return { siteData, siteDataLoading };
}

interface LiveWorkspaceProps {
  onViewDemo: () => void;
  welcomeDismissed: boolean;
  onDismissWelcome: () => void;
}

/** Real assessments against the API. Mounted per user (keyed on uid), so state never leaks between sessions. */
export default function LiveWorkspace({ onViewDemo, welcomeDismissed, onDismissWelcome }: LiveWorkspaceProps) {
  const auth = useAuth();
  const user = auth.user;
  const run = useSiteRun(checkLiveCapacity);
  const { siteData, siteDataLoading } = useSiteData(run.currentPosition);
  const [postcode, setPostcode] = useState('SE1 7PB');
  const lastRunPostcodeRef = useRef<string | null>(null);

  // Google key (BYOK), for the signed-in user only. Local mode (no Firebase config) has no key UI.
  const [keyStatus, setKeyStatus] = useState<KeyStatus | null>(null);
  const [keyPanelOpen, setKeyPanelOpen] = useState(false);

  const uid = user?.uid;
  useEffect(() => {
    if (!uid) return;
    let stale = false;
    getKeyStatus()
      .then((status) => !stale && setKeyStatus(status))
      .catch(() => !stale && setKeyStatus({ configured: false, last4: null, updated_at: null }));
    return () => {
      stale = true;
    };
  }, [uid]);

  const handleStartRun = async (flexibleOverride?: boolean) => {
    const input = postcode.trim();
    const isUrl = /^https?:\/\//.test(input);
    let target = isUrl ? 'SE1 7PB' : input;
    const flexible = flexibleOverride ?? run.flexibleConnection;

    run.setStarting(true);
    // Pin dragged away from the last assessed postcode (and the postcode text untouched): assess where the pin is.
    // A run starts from a postcode, so use the nearest one and keep the pin where the user put it.
    let pin: [number, number] | undefined;
    const pinMoved = distanceKm(run.initialCenter, run.currentPosition) > 0.05;
    if (!isUrl && pinMoved && postcode === lastRunPostcodeRef.current) {
      const nearest = await nearestPostcode(run.currentPosition);
      if (nearest) {
        target = nearest;
        setPostcode(nearest);
        pin = run.currentPosition;
      }
    }
    lastRunPostcodeRef.current = target;

    const center = (!isUrl && (await geocodePostcode(target))) || run.currentPosition;
    run.begin(center, pin);

    try {
      const payload: AssessmentRequest = isUrl
        ? { link: input, property_url: input, flexible_connection: flexible }
        : { postcode: target, flexible_connection: flexible };
      const res = await startRun(payload);
      run.track(res.run_id);
    } catch (err) {
      run.setCapacityLoading(false);
      if (err instanceof ApiError && err.status === 401 && JSON.stringify(err.data).includes('missing_google_key')) {
        setKeyStatus({ configured: false, last4: null, updated_at: null });
        setKeyPanelOpen(true);
        run.setErrorMsg('Add your Google AI key in Settings to run a live assessment.');
      } else if (err instanceof ApiError && err.status === 401) {
        run.setErrorMsg('Your session has expired. Sign in again to continue.');
      } else {
        run.setErrorMsg(err instanceof Error ? err.message : 'Could not start the assessment.');
      }
    } finally {
      run.setStarting(false);
    }
  };

  const handleReset = () => {
    run.reset();
    setPostcode('');
    lastRunPostcodeRef.current = null;
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      {user && (
        <>
          <KeyPanel open={keyPanelOpen} onOpenChange={setKeyPanelOpen} status={keyStatus} onStatusChange={setKeyStatus} />
          <FirstLoadModal
            open={keyStatus?.configured === false && !welcomeDismissed && !keyPanelOpen}
            onConfigureKey={() => setKeyPanelOpen(true)}
            onViewDemo={onViewDemo}
            onDismiss={onDismissWelcome}
          />
        </>
      )}

      <AppHeader onHome={handleReset} runId={run.runId} onResetRun={handleReset}>
        {user && (
          <div className="flex items-center gap-2 text-xs">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setKeyPanelOpen(true)}
              className="gap-1.5 text-xs h-8 px-2.5 sm:px-3 rounded-xl border-border cursor-pointer hover:bg-muted/80 transition-colors"
              title="Settings & Google AI Key"
              aria-label="Settings"
            >
              <Settings className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="hidden sm:inline">Settings</span>
              {keyStatus?.configured && (
                <span className="text-[10px] font-mono bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-500/20">
                  ••••{keyStatus.last4}
                </span>
              )}
            </Button>
            <span
              className="text-muted-foreground hidden md:inline max-w-[160px] truncate text-[11px] font-medium"
              title={user.email ?? undefined}
            >
              {user.email}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void auth.signOut()}
              className="gap-1.5 text-xs h-8 px-2.5 rounded-xl cursor-pointer text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Logout</span>
            </Button>
          </div>
        )}
      </AppHeader>

      <main className="flex-1 max-w-[1800px] w-full mx-auto p-4 sm:p-6 space-y-6">
        <RunView
          run={run}
          onConfirm={() => void run.submitDecision()}
          onReset={handleReset}
          onRetryFlexible={() => void handleStartRun(true)}
          locationBar={
            <div className="flex flex-col md:flex-row gap-3">
              <PostcodeInput
                value={postcode}
                onChange={setPostcode}
                onSubmit={() => void handleStartRun()}
                placeholder="Enter UK Postcode (e.g. SE1 7PB) or Property URL"
                disabled={run.starting}
              />
              <Button
                type="button"
                onClick={() => void handleStartRun()}
                disabled={run.starting || !postcode.trim()}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-6 h-11 rounded-xl gap-2 shadow-xs cursor-pointer text-sm"
              >
                <Search className="w-4 h-4 stroke-[2.5]" />
                <span>{run.starting ? 'Screening Grid...' : 'Screen Location'}</span>
              </Button>
            </div>
          }
          siteData={siteData}
          siteDataLoading={siteDataLoading}
        />
      </main>
    </div>
  );
}
