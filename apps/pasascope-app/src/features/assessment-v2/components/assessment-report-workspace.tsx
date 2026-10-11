"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AssessmentV2Client,
  type AssessmentV2Report,
  type AssessmentV2ReportLineageItem,
} from "@/services/assessment-v2-client";

export type AssessmentReportClient = Pick<
  AssessmentV2Client,
  | "getCurrentReport"
  | "getReport"
  | "updateReportDraft"
  | "signOffReport"
  | "createReportAmendment"
  | "getReportLineage"
  | "getReportExportPdfUrl"
>;

type AssessmentReportWorkspaceProps = {
  assessmentId: string;
  client?: AssessmentReportClient;
};

const defaultClient = new AssessmentV2Client();

export function AssessmentReportWorkspace({
  assessmentId,
  client = defaultClient,
}: AssessmentReportWorkspaceProps) {
  const [report, setReport] = useState<AssessmentV2Report | null>(null);
  const [lineage, setLineage] = useState<AssessmentV2ReportLineageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [signing, setSigning] = useState(false);
  const [amending, setAmending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form states for draft edit
  const [reportTitle, setReportTitle] = useState("");
  const [clinicalSummary, setClinicalSummary] = useState("");
  const [markdownContent, setMarkdownContent] = useState("");

  // Modals
  const [showSignModal, setShowSignModal] = useState(false);
  const [showAmendModal, setShowAmendModal] = useState(false);
  const [amendmentReason, setAmendmentReason] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rep = await client.getCurrentReport(assessmentId);
      setReport(rep);
      setReportTitle(rep.report_title);
      setClinicalSummary(rep.clinical_summary);
      setMarkdownContent(rep.markdown_content);

      if (rep.report_id) {
        try {
          const lin = await client.getReportLineage(assessmentId, rep.report_id);
          setLineage(lin);
        } catch {
          // Lineage might be empty for new drafts
        }
      }
    } catch (err: unknown) {
      setError("ยังไม่มีร่างรายงานสำหรับรอบการประเมินนี้ กรุณาทำการตรวจทานข้อสังเกตและสร้างร่างก่อน");
    } finally {
      setLoading(false);
    }
  }, [assessmentId, client]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleSaveDraft = async () => {
    if (!report) return;
    setSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const updated = await client.updateReportDraft(assessmentId, report.report_id, {
        report_title: reportTitle.trim(),
        clinical_summary: clinicalSummary.trim(),
        markdown_content: markdownContent,
        expected_version: report.version,
      });
      setReport(updated);
      setSuccessMessage("บันทึกร่างรายงานเรียบร้อยแล้ว");
    } catch (err: unknown) {
      setError("เกิดข้อผิดพลาดในการบันทึกร่างรายงาน (อาจมีการแก้ไขจากเซสชันอื่นหรือรายงานถูกลงนามแล้ว)");
    } finally {
      setSaving(false);
    }
  };

  const handleSignOff = async () => {
    if (!report) return;
    setSigning(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const signed = await client.signOffReport(assessmentId, report.report_id, {
        expected_version: report.version,
      });
      setReport(signed);
      setShowSignModal(false);
      setSuccessMessage("ลงนามรับรองรายงานเรียบร้อยแล้ว รายงานถูกบันทึกเป็น Snapshot ถาวร");
      // Reload lineage
      const lin = await client.getReportLineage(assessmentId, signed.report_id);
      setLineage(lin);
    } catch (err: unknown) {
      setError("ไม่สามารถลงนามรับรองรายงานได้ กรุณาตรวจสอบเงื่อนไขความพร้อมของเซิร์ฟเวอร์");
    } finally {
      setSigning(false);
    }
  };

  const handleCreateAmendment = async () => {
    if (!report || !amendmentReason.trim()) return;
    setAmending(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const newDraft = await client.createReportAmendment(assessmentId, report.report_id, {
        amendment_reason: amendmentReason.trim(),
        expected_version: report.version,
      });
      setReport(newDraft);
      setReportTitle(newDraft.report_title);
      setClinicalSummary(newDraft.clinical_summary);
      setMarkdownContent(newDraft.markdown_content);
      setShowAmendModal(false);
      setAmendmentReason("");
      setSuccessMessage(`สร้างฉบับแก้ไขเพิ่มเติม (ลำดับที่ ${newDraft.amendment_sequence}) สำเร็จ`);
      const lin = await client.getReportLineage(assessmentId, newDraft.report_id);
      setLineage(lin);
    } catch (err: unknown) {
      setError("เกิดข้อผิดพลาดในการสร้างฉบับแก้ไขเพิ่มเติม");
    } finally {
      setAmending(false);
    }
  };

  if (loading) {
    return (
      <section
        className="workspace-panel rounded-xl border border-line bg-white p-6 shadow-sm  "
        aria-busy="true"
      >
        <div className="flex items-center space-x-3 text-ink-muted">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          <p className="text-sm font-medium">กำลังโหลดข้อมูลรายงานทางคลินิก…</p>
        </div>
      </section>
    );
  }

  if (!report) {
    return (
      <section className="workspace-panel rounded-xl border border-line bg-white p-6 shadow-sm  ">
        <div className="text-center">
          <h3 className="text-base font-bold text-ink ">
            ยังไม่พบร่างรายงาน (No Report Draft Available)
          </h3>
          <p className="mt-2 text-xs text-ink-muted">
            กรุณาไปที่หน้าการตรวจทานทางคลินิก (Clinical Review) เพื่อตรวจทานข้อสังเกตและสร้างร่างรายงานฉบับแรก
          </p>
          <div className="mt-4">
            <Link
              href={`/assessments/${encodeURIComponent(assessmentId)}/review`}
              className="inline-flex items-center rounded-lg bg-brand px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-brand"
            >
              ← ไปยังหน้าตรวจทานข้อสังเกต (Clinical Review)
            </Link>
          </div>
        </div>
      </section>
    );
  }

  const isDraft = report.status === "draft";
  const isSigned = report.status === "signed_off" || report.status === "amended";
  const isReady = report.readiness.is_ready;

  return (
    <section className="workspace-panel space-y-6 rounded-xl border border-line bg-white p-6 shadow-sm  ">
      {/* Header & Status */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-line pb-4 ">
        <div>
          <div className="flex items-center space-x-2">
            <span className="rounded bg-brand-soft px-2 py-0.5 text-xs font-semibold uppercase text-brand-strong  ">
              Clinical Report (Slice C2)
            </span>
            <h2 className="text-lg font-bold text-ink ">
              รายงานการประเมินและการลงนามรับรอง
            </h2>
          </div>
          <p className="mt-1 text-xs text-ink-muted">
            Report ID: <span className="font-mono">{report.report_id}</span> | สถานะ:{" "}
            <span
              className={`font-bold ${
                report.status === "signed_off"
                  ? "text-[color:var(--color-success-text)]"
                  : report.status === "draft"
                  ? "text-[color:var(--color-warning-text)]"
                  : "text-ink-muted"
              }`}
            >
              {report.status === "signed_off"
                ? "ลงนามรับรองแล้ว (Signed-off)"
                : report.status === "draft"
                ? "ร่างรายงาน (Draft)"
                : report.status}
            </span>{" "}
            {report.amendment_sequence > 0 && `(ฉบับแก้ไขที่ ${report.amendment_sequence})`}
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Link
            href={`/assessments/${encodeURIComponent(assessmentId)}/review`}
            className="inline-flex items-center rounded-lg border border-line-strong bg-white px-3 py-1.5 text-xs font-semibold text-ink shadow-sm hover:bg-surface-soft   "
          >
            ← หน้าตรวจทานข้อสังเกต
          </Link>
          {isSigned && (
            <a
              href={client.getReportExportPdfUrl(assessmentId, report.report_id)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center rounded-lg bg-brand px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-brand"
            >
              ดาวน์โหลด PDF ภาษาไทย 📄
            </a>
          )}
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-lg bg-[color:var(--color-danger-bg)] p-4 text-xs font-medium text-[color:var(--color-danger-text)]  "
        >
          {error}
        </div>
      )}

      {successMessage && (
        <div
          role="status"
          className="rounded-lg bg-[color:var(--color-success-bg)] p-4 text-xs font-medium text-[color:var(--color-success-text)]  "
        >
          {successMessage}
        </div>
      )}

      {/* Server-Side Readiness Banner */}
      {isDraft && (
        <div
          className={`rounded-lg border p-4 text-xs ${
            isReady
              ? "border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]   "
              : "border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]   "
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="font-bold">
                {isReady
                  ? "✓ เซิร์ฟเวอร์พร้อมสำหรับการลงนาม (Server Readiness Passed)"
                  : "⚠ เงื่อนไขความพร้อมสำหรับการลงนามยังไม่ครบ (Sign-off Blocked)"}
              </span>
            </div>
            {isReady && (
              <button
                type="button"
                onClick={() => setShowSignModal(true)}
                className="inline-flex items-center rounded-lg bg-brand px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-brand"
              >
                ลงนามรับรองรายงาน (Sign-off Report)
              </button>
            )}
          </div>

          {!isReady && report.readiness.blockers.length > 0 && (
            <ul className="mt-2 list-inside list-disc space-y-1 text-[11px] text-[color:var(--color-warning-text)] ">
              {report.readiness.blockers.map((b, idx) => (
                <li key={idx}>{b}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Signed Snapshot Metadata Card */}
      {isSigned && (
        <div className="rounded-lg border border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] p-4 text-xs  ">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <span className="font-bold text-[color:var(--color-success-text)] ">
                ข้อมูลการลงนามรับรอง (Immutable Signed Snapshot)
              </span>
              <p className="mt-1 text-ink ">
                ผู้ลงนาม: <strong>{report.signer_name || report.signer_id}</strong> (
                {report.signer_role || "assigned_clinician"}) | เวลาที่ลงนาม:{" "}
                {report.signed_at ? new Date(report.signed_at).toLocaleString() : "—"}
              </p>
              <p className="mt-1 font-mono text-[11px] text-ink-muted ">
                SHA-256 Hash: {report.snapshot_sha256}
              </p>
            </div>

            <button
              type="button"
              onClick={() => setShowAmendModal(true)}
              className="inline-flex items-center rounded-lg border border-line-strong bg-white px-3 py-1.5 text-xs font-semibold text-ink shadow-sm hover:bg-surface-soft   "
            >
              แก้ไขเพิ่มเติม (Amend Report) ✏️
            </button>
          </div>
        </div>
      )}

      {/* Draft Content Form / Preview */}
      <div className="space-y-4">
        <div>
          <label htmlFor="report-title-input" className="block text-xs font-semibold text-ink ">
            ชื่อรายงาน (Report Title):
          </label>
          <input
            id="report-title-input"
            type="text"
            disabled={!isDraft}
            value={reportTitle}
            onChange={(e) => setReportTitle(e.target.value)}
            className="mt-1 w-full rounded-lg border border-line-strong p-2 text-xs font-medium text-ink focus:outline-none focus:ring-1 focus:ring-[color:var(--color-focus-ring)] disabled:bg-surface-muted    "
          />
        </div>

        <div>
          <label htmlFor="clinical-summary-text" className="block text-xs font-semibold text-ink ">
            บทสรุปทางคลินิก (Clinical Summary):
          </label>
          <textarea
            id="clinical-summary-text"
            rows={3}
            disabled={!isDraft}
            value={clinicalSummary}
            onChange={(e) => setClinicalSummary(e.target.value)}
            className="mt-1 w-full rounded-lg border border-line-strong p-2 text-xs text-ink focus:outline-none focus:ring-1 focus:ring-[color:var(--color-focus-ring)] disabled:bg-surface-muted    "
          />
        </div>

        <div>
          <label htmlFor="markdown-content-text" className="block text-xs font-semibold text-ink ">
            เนื้อหารายงาน Markdown (Markdown Content):
          </label>
          <textarea
            id="markdown-content-text"
            rows={12}
            disabled={!isDraft}
            value={markdownContent}
            onChange={(e) => setMarkdownContent(e.target.value)}
            className="mt-1 w-full rounded-lg border border-line-strong font-mono p-3 text-xs text-ink focus:outline-none focus:ring-1 focus:ring-[color:var(--color-focus-ring)] disabled:bg-surface-muted    "
          />
        </div>

        {isDraft && (
          <div className="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={() => void handleSaveDraft()}
              disabled={saving}
              className="inline-flex items-center rounded-lg bg-brand px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-brand disabled:opacity-50"
            >
              {saving ? "กำลังบันทึก…" : "บันทึกการแก้ไขร่างรายงาน (Save Draft)"}
            </button>
          </div>
        )}
      </div>

      {/* Amendment Lineage Section */}
      {lineage.length > 0 && (
        <div className="space-y-3 border-t border-line pt-4 ">
          <h3 className="text-sm font-bold text-ink ">
            ประวัติการแก้ไขและสายวิวัฒนาการรายงาน (Amendment Lineage)
          </h3>

          <div className="divide-y divide-line rounded-lg border border-line bg-white text-xs   ">
            {lineage.map((item) => (
              <div key={item.report_id} className="p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-ink ">
                      ฉบับที่ {item.amendment_sequence === 0 ? "ตั้งต้น (Original)" : `แก้ไข ${item.amendment_sequence}`}
                    </span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                        item.status === "signed_off"
                          ? "bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]  "
                          : item.status === "amended"
                          ? "bg-surface-muted text-ink-muted  "
                          : "bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]  "
                      }`}
                    >
                      {item.status}
                    </span>
                  </div>
                  <span className="text-[11px] text-ink-muted">
                    {item.signed_at ? new Date(item.signed_at).toLocaleString() : "ยังไม่ลงนาม"}
                  </span>
                </div>

                {item.amendment_reason && (
                  <p className="mt-1 text-ink-muted ">
                    <span className="font-semibold">เหตุผลการแก้ไข: </span>
                    {item.amendment_reason}
                  </p>
                )}

                {item.snapshot_sha256 && (
                  <p className="mt-1 font-mono text-[10px] text-ink-muted">
                    SHA-256: {item.snapshot_sha256.slice(0, 24)}…
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sign-off Confirmation Modal */}
      {showSignModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="sign-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        >
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl ">
            <h3 id="sign-modal-title" className="text-base font-bold text-ink ">
              ยืนยันการลงนามรับรองรายงาน (Sign-off Confirmation)
            </h3>
            <div className="mt-3 text-xs text-ink-muted space-y-2">
              <p>
                การลงนามรับรองจะบันทึก Snapshot รายงานอย่างถาวร (Immutable Snapshot) พร้อมสร้าง Deterministic SHA-256
                Hash ซึ่งไม่สามารถเปลี่ยนแปลงได้
              </p>
              <p className="font-medium text-[color:var(--color-warning-text)] ">
                หากจำเป็นต้องปรับปรุงข้อความในอนาคต จะต้องดำเนินการผ่านกระบวนการออกฉบับแก้ไขเพิ่มเติม (Amendment Lineage)
                เท่านั้น
              </p>
            </div>
            <div className="mt-5 flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowSignModal(false)}
                className="rounded-lg px-3 py-1.5 text-xs text-ink-muted hover:text-ink "
              >
                ยกเลิก
              </button>
              <button
                type="button"
                disabled={signing}
                onClick={() => void handleSignOff()}
                className="rounded-lg bg-brand px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-brand disabled:opacity-50"
              >
                {signing ? "กำลังลงนาม…" : "ยืนยันการลงนามรับรอง"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Amendment Modal */}
      {showAmendModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="amend-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        >
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl ">
            <h3 id="amend-modal-title" className="text-base font-bold text-ink ">
              สร้างฉบับแก้ไขเพิ่มเติม (Create Report Amendment)
            </h3>
            <p className="mt-2 text-xs text-ink-muted ">
              การแก้ไขเพิ่มเติมจะคัดลอกเนื้อหาเดิมไปเป็นร่างใหม่ (Draft) และคง Snapshot ฉบับเดิมไว้ในประวัติ
            </p>
            <div className="mt-3">
              <label htmlFor="amend-reason-input" className="block text-xs font-semibold text-ink ">
                ระบุเหตุผลในการแก้ไข (Amendment Reason):
              </label>
              <textarea
                id="amend-reason-input"
                rows={3}
                value={amendmentReason}
                onChange={(e) => setAmendmentReason(e.target.value)}
                placeholder="เช่น ปรับปรุงข้อความตามหลักฐานเพิ่มเติมจากการสังเกตในห้องตรวจ..."
                className="mt-1 w-full rounded-lg border border-line-strong p-2 text-xs text-ink focus:outline-none focus:ring-1 focus:ring-[color:var(--color-focus-ring)]   "
              />
            </div>
            <div className="mt-5 flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowAmendModal(false)}
                className="rounded-lg px-3 py-1.5 text-xs text-ink-muted hover:text-ink "
              >
                ยกเลิก
              </button>
              <button
                type="button"
                disabled={!amendmentReason.trim() || amending}
                onClick={() => void handleCreateAmendment()}
                className="rounded-lg bg-brand px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-brand disabled:opacity-50"
              >
                {amending ? "กำลังดำเนินการ…" : "สร้างร่างฉบับแก้ไข"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
