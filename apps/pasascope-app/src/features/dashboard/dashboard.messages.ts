import { defineMessages } from "@/i18n/messages";

/** Dashboard header and its unavailable states. The panels are still English-only. */
export const dashboardMessages = defineMessages({
  en: {
    eyebrow: "Clinical Overview",
    title: "Dashboard",
    description: "The cases in your care, how far each session has moved through the workflow, and descriptive language measures over time.",
    organization: (id: string) => `Organization: ${id}`,
    updated: (date: string) => `Updated ${date}`,
    loading: "Loading practice summary…",
    unavailable: {
      label: "Dashboard unavailable",
      title: "Practice summary could not be loaded",
      signInChip: "Sign-in required",
      offlineChip: "Server unavailable",
      denied: "Your session is not authorized to view the practice summary. Sign in again, or ask your organization administrator.",
      offline: "The summary did not load because the server did not respond. Nothing was changed. Try again in a moment.",
      backToToday: "Back to Today",
      openCases: "Open Cases",
    },
  },
  th: {
    eyebrow: "ภาพรวมทางคลินิก",
    title: "ภาพรวม",
    description: "เคสที่คุณดูแล ความคืบหน้าของแต่ละเซสชันในขั้นตอนการทำงาน และค่าพรรณนาทางภาษาตามช่วงเวลา",
    organization: (id: string) => `องค์กร: ${id}`,
    updated: (date: string) => `ปรับปรุงเมื่อ ${date}`,
    loading: "กำลังโหลดข้อมูลสรุป…",
    unavailable: {
      label: "ไม่สามารถแสดงหน้าภาพรวมได้",
      title: "โหลดข้อมูลสรุปไม่สำเร็จ",
      signInChip: "ต้องลงชื่อเข้าใช้",
      offlineChip: "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้",
      denied: "เซสชันของคุณไม่มีสิทธิ์ดูข้อมูลสรุป กรุณาลงชื่อเข้าใช้อีกครั้ง หรือติดต่อผู้ดูแลองค์กร",
      offline: "โหลดข้อมูลสรุปไม่ได้เพราะเซิร์ฟเวอร์ไม่ตอบสนอง ไม่มีข้อมูลใดถูกเปลี่ยนแปลง ลองอีกครั้งในอีกสักครู่",
      backToToday: "กลับไปหน้าวันนี้",
      openCases: "เปิดรายการเคส",
    },
  },
});
