'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { CheckCircle2, KeyRound, Loader2, ShieldAlert, XCircle } from 'lucide-react';
import { deleteKey, KeyStatus, saveKey, testKey } from '../lib/api';

interface KeyPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The saved key state, or null while it is still loading. */
  status: KeyStatus | null;
  onStatusChange: (status: KeyStatus) => void;
}

type Feedback = { kind: 'ok' | 'error'; text: string } | null;

export default function KeyPanel({ open, onOpenChange, status, onStatusChange }: KeyPanelProps) {
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState<'test' | 'save' | 'delete' | null>(null);
  const [feedback, setFeedback] = useState<Feedback>(null);

  // Never keep a typed key around once the panel closes.
  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setDraft('');
      setFeedback(null);
    }
    onOpenChange(next);
  };

  const typed = draft.trim();
  const canTest = !busy && (typed.length > 0 || !!status?.configured);

  const run = async (kind: 'test' | 'save' | 'delete', fn: () => Promise<void>) => {
    setBusy(kind);
    setFeedback(null);
    try {
      await fn();
    } catch (err) {
      setFeedback({ kind: 'error', text: err instanceof Error ? err.message : 'Something went wrong' });
    } finally {
      setBusy(null);
    }
  };

  const handleTest = () =>
    run('test', async () => {
      const res = await testKey(typed || undefined);
      setFeedback(
        res.ok
          ? { kind: 'ok', text: res.message || 'Gemini accepted the key.' }
          : { kind: 'error', text: res.message || 'Gemini rejected the key.' }
      );
    });

  const handleSave = () =>
    run('save', async () => {
      const saved = await saveKey(typed);
      onStatusChange(saved);
      setDraft('');
      setFeedback({ kind: 'ok', text: 'Key saved.' });
    });

  const handleDelete = () =>
    run('delete', async () => {
      await deleteKey();
      onStatusChange({ configured: false, last4: null, updated_at: null });
      setFeedback({ kind: 'ok', text: 'Key deleted.' });
    });

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="w-4 h-4 text-emerald-600" />
            Google AI key
          </DialogTitle>
          <DialogDescription>
            Bessible runs Gemini with your own key, so the team&apos;s quota is never used. This is the only key it needs.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="text-xs rounded-lg border border-border bg-muted/40 px-3 py-2">
            {status === null ? (
              <span className="text-muted-foreground">Checking saved key…</span>
            ) : status.configured ? (
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Key saved: <span className="font-mono">••••{status.last4}</span>
              </span>
            ) : (
              <span className="text-muted-foreground">No key saved yet.</span>
            )}
          </div>

          <Input
            type="password"
            autoComplete="off"
            spellCheck={false}
            placeholder={status?.configured ? 'Paste a new key to replace it' : 'Paste your Google AI (Gemini) key'}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="font-mono text-xs h-10"
          />

          {feedback && (
            <div
              role="status"
              className={`flex items-start gap-1.5 text-xs ${
                feedback.kind === 'ok' ? 'text-emerald-700 dark:text-emerald-300' : 'text-destructive'
              }`}
            >
              {feedback.kind === 'ok' ? (
                <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              ) : (
                <XCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              )}
              <span>{feedback.text}</span>
            </div>
          )}

          <p className="flex items-start gap-1.5 text-[11px] text-muted-foreground">
            <ShieldAlert className="w-3.5 h-3.5 mt-0.5 shrink-0 text-amber-500" />
            <span>
              The key is stored encrypted on the server and is never shown again. Use a restricted or throwaway key.
            </span>
          </p>
        </div>

        <DialogFooter className="sm:justify-between">
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={!!busy || !status?.configured}
          >
            {busy === 'delete' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Delete key
          </Button>
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" onClick={handleTest} disabled={!canTest}>
              {busy === 'test' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Test key
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleSave}
              disabled={!!busy || typed.length === 0}
              className="bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              {busy === 'save' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Save key
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
