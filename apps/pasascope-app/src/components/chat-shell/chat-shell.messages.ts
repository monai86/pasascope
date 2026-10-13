import { defineMessages } from "@/i18n/messages";

/** Strings only the chat shell's frame uses; kept apart so the workbench shell does not carry them. */
export const chatShellMessages = defineMessages({
  en: {
    nav: { home: "Home", cases: "Cases", reports: "Reports", settings: "Settings" },
    backHome: "Back to home",
    closePanel: "Close panel",
  },
  th: {
    nav: { home: "หน้าหลัก", cases: "เคส", reports: "รายงาน", settings: "ตั้งค่า" },
    backHome: "กลับหน้าหลัก",
    closePanel: "ปิดแผง",
  },
});
