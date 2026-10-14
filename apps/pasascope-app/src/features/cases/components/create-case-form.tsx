"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { ActionButton } from "@/components/action-button";
import {
  createCaseSchema,
  type CreateCaseFormValues,
} from "@/features/cases/schemas/create-case-schema";
import { casesMessages } from "@/features/cases/cases.messages";
import { casesAdapter } from "@/features/cases/services/cases-adapter";
import { useMessages } from "@/i18n/locale-provider";

const fieldClassName =
  "min-h-11 w-full rounded-card border border-line bg-surface px-4 text-sm text-ink outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]";

export function CreateCaseForm({ onCancel }: { onCancel: () => void }) {
  const router = useRouter();
  const t = useMessages(casesMessages).create;
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<CreateCaseFormValues>({
    resolver: zodResolver(createCaseSchema),
    defaultValues: { child_code: "", nickname: "", language: "Thai", notes: "" },
  });

  async function submit(values: CreateCaseFormValues) {
    try {
      const created = await casesAdapter.create(values);
      router.push(`/cases/${encodeURIComponent(created.case_id)}`);
      router.refresh();
    } catch {
      setError("root", {
        message: t.failed,
      });
    }
  }

  return (
    <section className="workspace-panel p-5" aria-labelledby="create-case-heading">
      <h2
        id="create-case-heading"
        className="text-lg font-semibold text-ink"
      >
        {t.title}
      </h2>
      <p className="mt-1 text-sm leading-6 text-ink-muted">
        {t.body}
      </p>
      <form className="mt-5 grid gap-4" onSubmit={handleSubmit(submit)} noValidate>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t.caseCode} error={errors.child_code?.message}>
            <input aria-label={t.caseCode} autoComplete="off" className={fieldClassName} {...register("child_code")} />
          </Field>
          <Field label={t.nickname} error={errors.nickname?.message} hint={t.nicknameHint}>
            <input aria-label={t.nickname} autoComplete="off" className={fieldClassName} {...register("nickname")} />
          </Field>
          <Field label={t.ageMonths} error={errors.age_months?.message}>
            <input
              aria-label={t.ageMonths}
              type="number"
              min="0"
              max="240"
              className={fieldClassName}
              {...register("age_months", { valueAsNumber: true })}
            />
          </Field>
          <Field label={t.language} error={errors.language?.message}>
            <input aria-label={t.language} autoComplete="off" className={fieldClassName} {...register("language")} />
          </Field>
        </div>
        <Field label={t.notes} error={errors.notes?.message} hint={t.notesHint}>
          <textarea aria-label={t.notes} rows={3} className={`${fieldClassName} py-3`} {...register("notes")} />
        </Field>
        {errors.root?.message ? (
          <p role="alert" className="text-sm text-[color:var(--color-danger-text)]">
            {errors.root.message}
          </p>
        ) : null}
        <div className="flex flex-col gap-3 sm:flex-row">
          <ActionButton type="submit" disabled={isSubmitting}>
            {isSubmitting ? t.saving : t.save}
          </ActionButton>
          <ActionButton type="button" tone="ghost" onClick={onCancel} disabled={isSubmitting}>
            {t.cancel}
          </ActionButton>
        </div>
      </form>
    </section>
  );
}

function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="grid content-start gap-1 text-sm font-medium text-ink">
      <span>{label}</span>
      {children}
      {error ? (
        <span className="text-xs text-[color:var(--color-danger-text)]">{error}</span>
      ) : hint ? (
        <span className="text-xs font-normal text-ink-muted">{hint}</span>
      ) : null}
    </label>
  );
}
