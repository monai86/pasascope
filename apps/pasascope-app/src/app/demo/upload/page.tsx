import Link from "next/link";
import { UploadCloud, CheckCircle2, FileAudio, ArrowRight } from "lucide-react";

export default function DemoUpload() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-semibold tracking-[-0.03em] text-ink">
          อัปโหลดไฟล์เสียง (Upload Audio)
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          อัปโหลดคลิปวิดีโอหรือเสียงจากเซสชันการบำบัดเพื่อถอดความและวิเคราะห์ทางภาษาพูด
        </p>
      </div>

      {/* Drag & Drop Zone */}
      <div className="relative flex flex-col items-center justify-center rounded-panel border-2 border-dashed border-line bg-white p-12 text-center transition hover:border-brand">
        <div className="flex h-12 w-12 items-center justify-center text-brand">
          <UploadCloud size={32} />
        </div>
        <h3 className="mt-4 text-lg font-semibold text-ink">
          ลากไฟล์มาวางที่นี่ หรือ คลิกเพื่อเลือกไฟล์
        </h3>
        <p className="mt-2 text-sm text-ink-muted">
          รองรับไฟล์วิดีโอและไฟล์เสียง เช่น .mp4, .wav, .m4a หรือไฟล์ถอดคำรหัส .cha
        </p>
        <span className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-surface-muted px-3 py-1 text-xs font-semibold text-ink-muted">
          ขนาดสูงสุด 100MB
        </span>
      </div>

      {/* Upload Progress (Static Showcase) */}
      <div className="rounded-panel border border-line bg-surface p-5">
        <div className="flex items-start gap-4">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]">
            <FileAudio size={20} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-3">
              <p className="truncate text-sm font-semibold text-ink">
                session_recording_ava_2026-07-05.wav
              </p>
              <span className="shrink-0 text-xs font-semibold text-[color:var(--color-success-text)] flex items-center gap-1">
                <CheckCircle2 size={12} />
                อัปโหลดสำเร็จ
              </span>
            </div>
            <p className="mt-1 text-xs text-ink-subtle">
              12.4 MB · ถอดความเสียงอัตโนมัติด้วย Whisper (Thai-English)
            </p>
            {/* Custom Progress Bar */}
            <div className="mt-3 h-1.5 w-full rounded-full bg-surface-muted overflow-hidden">
              <div className="h-full w-full rounded-full bg-brand" />
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-between border-t border-line pt-6">
        <Link
          href="/demo/dashboard"
          className="inline-flex min-h-11 items-center justify-center rounded-full border border-line bg-white px-5 text-sm font-semibold text-ink transition hover:bg-surface-soft"
        >
          กลับหน้าหลัก
        </Link>
        <Link
          href="/demo/transcript"
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-brand px-6 text-sm font-semibold text-white transition hover:bg-brand-strong"
        >
          ถัดไป: ดูบทสนทนา
          <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
}
