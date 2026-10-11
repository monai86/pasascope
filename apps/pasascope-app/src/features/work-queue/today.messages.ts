import type { TodayQueueGroupKey, TodayTaskKind } from "@/features/work-queue/today-workbench-model";
import { defineMessages } from "@/i18n/messages";

type TaskCopy = { task: string; reason: string; action: string };
type GroupCopy = { label: string; description: string };

type TodayCopy = {
  title: string;
  description: string;
  startSession: string;
  loading: string;
  error: { title: string; description: string; retry: string };
  empty: { title: string; description: string; action: string };
  nextUp: string;
  summaryLabel: string;
  summary: { needsAction: string; readyForReview: string; readyForSignoff: string };
  queueTitle: string;
  itemCount: (count: number) => string;
  notScheduled: string;
  dateUnavailable: string;
  groups: Record<TodayQueueGroupKey, GroupCopy>;
  tasks: Record<TodayTaskKind, TaskCopy>;
  priority: Record<"low" | "moderate" | "high", string>;
  context: { title: string; loading: string; error: string; recentCases: string; empty: string };
};

export const todayMessages = defineMessages<TodayCopy>({
  en: {
    title: "Today",
    description: "What needs your decision next, in one prioritized list. Queue status is operational, not a clinical conclusion.",
    startSession: "Start session",
    loading: "Loading today’s work queue…",
    error: {
      title: "We couldn’t load your work queue",
      description: "Check your connection and try again.",
      retry: "Retry work queue",
    },
    empty: {
      title: "No work requires attention right now.",
      description: "Start a session or review a case when you’re ready.",
      action: "Start a session",
    },
    nextUp: "Next up for you",
    summaryLabel: "Work queue summary",
    summary: { needsAction: "Needs action", readyForReview: "Ready for review", readyForSignoff: "Ready for sign-off" },
    queueTitle: "Prioritized queue",
    itemCount: (count) => `${count} ${count === 1 ? "item" : "items"}`,
    notScheduled: "Not scheduled",
    dateUnavailable: "Unavailable",
    groups: {
      needs_action: { label: "Needs action", description: "Blocked, stale, failed, or incomplete work requiring a therapist decision." },
      processing: { label: "Processing", description: "Backend work is still running. No completion is assumed." },
      ready_for_review: { label: "Ready for review", description: "Persisted transcript or report material is ready for therapist review." },
      ready_for_signoff: { label: "Ready for sign-off", description: "Reviewed report drafts awaiting the therapist’s final decision." },
      recently_completed: { label: "Recently completed", description: "Recently signed work available as an immutable record." },
    },
    tasks: {
      report_regeneration: { task: "Report regeneration", reason: "A newer transcript invalidated the existing report draft.", action: "Regenerate report" },
      report_safety_review: { task: "Report safety review", reason: "The persisted report is blocked or failed and requires therapist review.", action: "Review report" },
      signed_report: { task: "Signed report", reason: "The signed snapshot is complete and remains immutable.", action: "View signed report" },
      report_signoff: { task: "Report sign-off", reason: "A reviewed report draft is ready for the therapist’s sign-off decision.", action: "Review for sign-off" },
      report_review: { task: "Report review", reason: "A persisted report draft is ready for therapist review.", action: "Review report" },
      session_processing: { task: "Session processing", reason: "Backend processing is still in progress.", action: "View case" },
      transcript_review_attested: { task: "Transcript review", reason: "The reviewed transcript is ready for the next backend-permitted workflow step.", action: "Open case" },
      transcript_review: { task: "Transcript review", reason: "The persisted session is ready for therapist transcript review.", action: "Open case" },
      session_followup: { task: "Session follow-up", reason: "The persisted session is blocked or failed and requires therapist action.", action: "Review case" },
      session_intake: { task: "Session intake", reason: "The persisted session is incomplete and needs the therapist’s next input.", action: "Continue case" },
      start_session: { task: "Start session", reason: "No persisted session is available for this case yet.", action: "Start session" },
    },
    priority: { low: "Low", moderate: "Moderate", high: "High" },
    context: {
      title: "Today context",
      loading: "Recent cases will appear in a moment.",
      error: "Connection unavailable — recent cases are not shown right now.",
      recentCases: "Recent cases",
      empty: "No recent cases yet.",
    },
  },
  th: {
    title: "วันนี้",
    description: "งานที่รอการตัดสินใจของคุณ เรียงตามลำดับความสำคัญในรายการเดียว สถานะในคิวบอกความคืบหน้าของงาน ไม่ใช่ข้อสรุปทางคลินิก",
    startSession: "เริ่มเซสชัน",
    loading: "กำลังโหลดคิวงานของวันนี้…",
    error: {
      title: "โหลดคิวงานไม่สำเร็จ",
      description: "ตรวจสอบการเชื่อมต่อแล้วลองอีกครั้ง",
      retry: "โหลดคิวงานอีกครั้ง",
    },
    empty: {
      title: "ตอนนี้ไม่มีงานที่ต้องดำเนินการ",
      description: "เริ่มเซสชันใหม่หรือเปิดดูเคสได้เมื่อพร้อม",
      action: "เริ่มเซสชันใหม่",
    },
    nextUp: "งานถัดไปของคุณ",
    summaryLabel: "สรุปคิวงาน",
    summary: { needsAction: "รอดำเนินการ", readyForReview: "พร้อมให้ทบทวน", readyForSignoff: "พร้อมลงนาม" },
    queueTitle: "คิวงานตามลำดับความสำคัญ",
    itemCount: (count) => `${count} รายการ`,
    notScheduled: "ยังไม่กำหนดวัน",
    dateUnavailable: "ไม่มีข้อมูล",
    groups: {
      needs_action: { label: "รอดำเนินการ", description: "งานที่ติดขัด ล้าสมัย ไม่สำเร็จ หรือยังไม่ครบ ซึ่งต้องให้นักบำบัดตัดสินใจ" },
      processing: { label: "กำลังประมวลผล", description: "ระบบยังประมวลผลอยู่ ยังไม่ถือว่าเสร็จ" },
      ready_for_review: { label: "พร้อมให้ทบทวน", description: "บทถอดเสียงหรือรายงานที่บันทึกไว้พร้อมให้นักบำบัดทบทวน" },
      ready_for_signoff: { label: "พร้อมลงนาม", description: "ร่างรายงานที่ทบทวนแล้ว รอการตัดสินใจขั้นสุดท้ายของนักบำบัด" },
      recently_completed: { label: "เสร็จล่าสุด", description: "งานที่ลงนามแล้วเมื่อไม่นานมานี้ เก็บเป็นบันทึกที่แก้ไขไม่ได้" },
    },
    tasks: {
      report_regeneration: { task: "สร้างรายงานใหม่", reason: "บทถอดเสียงฉบับใหม่ทำให้ร่างรายงานเดิมใช้ไม่ได้", action: "สร้างรายงานใหม่" },
      report_safety_review: { task: "ตรวจสอบรายงานที่ถูกระงับ", reason: "รายงานที่บันทึกไว้ถูกระงับหรือไม่สำเร็จ ต้องให้นักบำบัดตรวจสอบ", action: "ตรวจรายงาน" },
      signed_report: { task: "รายงานที่ลงนามแล้ว", reason: "ฉบับที่ลงนามแล้วสมบูรณ์และแก้ไขไม่ได้", action: "ดูรายงานที่ลงนามแล้ว" },
      report_signoff: { task: "ลงนามรายงาน", reason: "ร่างรายงานที่ทบทวนแล้วพร้อมให้นักบำบัดตัดสินใจลงนาม", action: "ทบทวนเพื่อลงนาม" },
      report_review: { task: "ทบทวนรายงาน", reason: "ร่างรายงานที่บันทึกไว้พร้อมให้นักบำบัดทบทวน", action: "ทบทวนรายงาน" },
      session_processing: { task: "กำลังประมวลผลเซสชัน", reason: "ระบบยังประมวลผลอยู่", action: "ดูเคส" },
      transcript_review_attested: { task: "ทบทวนบทถอดเสียง", reason: "บทถอดเสียงที่ทบทวนแล้วพร้อมสำหรับขั้นตอนถัดไป", action: "เปิดเคส" },
      transcript_review: { task: "ทบทวนบทถอดเสียง", reason: "เซสชันที่บันทึกไว้พร้อมให้นักบำบัดทบทวนบทถอดเสียง", action: "เปิดเคส" },
      session_followup: { task: "ติดตามเซสชัน", reason: "เซสชันที่บันทึกไว้ถูกระงับหรือไม่สำเร็จ ต้องให้นักบำบัดดำเนินการ", action: "ตรวจเคส" },
      session_intake: { task: "รับข้อมูลเซสชัน", reason: "เซสชันที่บันทึกไว้ยังไม่ครบ รอข้อมูลถัดไปจากนักบำบัด", action: "ทำเคสต่อ" },
      start_session: { task: "เริ่มเซสชัน", reason: "เคสนี้ยังไม่มีเซสชันที่บันทึกไว้", action: "เริ่มเซสชัน" },
    },
    priority: { low: "ต่ำ", moderate: "ปานกลาง", high: "สูง" },
    context: {
      title: "บริบทของวันนี้",
      loading: "เคสล่าสุดจะแสดงในอีกสักครู่",
      error: "เชื่อมต่อไม่ได้ จึงยังไม่แสดงเคสล่าสุด",
      recentCases: "เคสล่าสุด",
      empty: "ยังไม่มีเคสล่าสุด",
    },
  },
});
