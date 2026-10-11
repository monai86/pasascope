"use client";

import { useId } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

/**
 * Asks for confirmation before an action that is hard to undo. The cancel
 * action is first in the tab order, so Enter on open never confirms.
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel,
  destructive = false,
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel: string;
  destructive?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const titleId = useId();
  const descriptionId = useId();

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : onCancel())} labelledBy={titleId} describedBy={descriptionId}>
      <DialogHeader>
        <DialogTitle id={titleId}>{title}</DialogTitle>
        <DialogDescription id={descriptionId}>{description}</DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="ghost" onClick={onCancel} disabled={busy}>
          {cancelLabel}
        </Button>
        <Button variant={destructive ? "danger" : "primary"} onClick={onConfirm} loading={busy}>
          {confirmLabel}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
