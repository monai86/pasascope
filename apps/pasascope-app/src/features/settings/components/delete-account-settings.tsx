"use client";

import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { accountSecurityMessages } from "@/features/settings/account-security.messages";
import { Row } from "@/features/settings/components/settings-rows";
import { deleteOwnAccount } from "@/features/settings/services/account-api";
import { useMessages } from "@/i18n/locale-provider";
import { ApiError } from "@/lib/api";
import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";

/** Deleting the account, behind typing its email address. */
export function DeleteAccountSettings({ email }: { email: string }) {
  const t = useMessages(accountSecurityMessages).deleteAccount;
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const titleId = useId();
  const descriptionId = useId();
  const matches = typed.trim().toLowerCase() === email.trim().toLowerCase();

  function close() {
    if (busy) return;
    setOpen(false);
    setTyped("");
    setError("");
  }

  async function remove() {
    if (!matches) return setError(t.mismatch);
    setBusy(true);
    setError("");
    try {
      await deleteOwnAccount();
    } catch (failure) {
      setBusy(false);
      // 502: the records are gone and only the sign-in account is left.
      setError(failure instanceof ApiError && failure.status === 502 ? t.partlyDeleted : t.failed);
      return;
    }
    await signOutSupabaseWorkspace();
    window.location.assign("/login?account=deleted");
  }

  return (
    <Row label={t.title} hint={t.hint}>
      <Button variant="danger" onClick={() => setOpen(true)}>{t.button}</Button>
      <Dialog open={open} onOpenChange={(next) => (next ? undefined : close())} labelledBy={titleId} describedBy={descriptionId}>
        <DialogHeader>
          <DialogTitle id={titleId}>{t.dialogTitle}</DialogTitle>
          <DialogDescription id={descriptionId}>{t.dialogBody}</DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            void remove();
          }}
        >
          <Field label={t.typeEmail(email)} error={error || undefined}>
            {(control) => (
              <Input
                {...control}
                type="email"
                autoComplete="off"
                value={typed}
                onChange={(event) => {
                  setTyped(event.target.value);
                  if (error) setError("");
                }}
                disabled={busy}
              />
            )}
          </Field>
          <DialogFooter>
            <Button variant="ghost" onClick={close} disabled={busy}>{t.cancel}</Button>
            <Button type="submit" variant="danger" loading={busy} disabled={busy || !matches}>
              {busy ? t.deleting : t.confirm}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>
    </Row>
  );
}
