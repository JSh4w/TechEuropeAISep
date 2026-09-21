'use client';

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { KeyRound, PlayCircle } from 'lucide-react';

interface FirstLoadModalProps {
  open: boolean;
  onConfigureKey: () => void;
  onViewDemo: () => void;
  /** Dismiss without choosing (Esc, backdrop, close button). */
  onDismiss: () => void;
}

/** Shown to a signed-in user who has no Google key saved yet. Final copy and layout to be decided later. */
export default function FirstLoadModal({ open, onConfigureKey, onViewDemo, onDismiss }: FirstLoadModalProps) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onDismiss()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add your Google AI key</DialogTitle>
          <DialogDescription>
            Real assessments run on your own Gemini key. Add one now, or look at a recorded example first.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          <Button
            type="button"
            onClick={onConfigureKey}
            className="bg-emerald-600 hover:bg-emerald-500 text-white gap-2"
          >
            <KeyRound className="w-4 h-4" />
            Configure key
          </Button>
          <Button type="button" variant="outline" onClick={onViewDemo} className="gap-2">
            <PlayCircle className="w-4 h-4" />
            View demo run
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
