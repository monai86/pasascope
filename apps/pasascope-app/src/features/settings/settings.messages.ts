import type { SettingsSection, SharedSettingsSection } from "@/features/settings/services/settings-access";
import { defineMessages } from "@/i18n/messages";

type Line = readonly [label: string, value: string];

type SettingsCopy = {
  page: { title: string; description: string };
  sections: Record<SettingsSection, string>;
  nav: { label: string; allCategories: string; choose: string; workspace: string; administration: string };
  /** One card per shared section; `lines` keep the order the screen renders them in. */
  cards: Record<SharedSettingsSection, { description: string; lines: readonly Line[] }>;
  privacyRequests: { title: string; unavailable: string; body: string; noClaim: string };
  /** Values shown instead of the demo ones when the workspace uses real sign-in. */
  signedIn: { fallbackName: string; dataMode: string; authentication: string };
};

export const settingsMessages = defineMessages<SettingsCopy>({
  en: {
    page: {
      title: "Settings",
      description: "Choose one workspace category. Organization administration appears only for authorized admins.",
    },
    sections: {
      account: "Account",
      organization: "Organization",
      accessibility: "Accessibility & Display",
      notifications: "Notifications",
      privacy: "Privacy & Security",
      export: "Export",
      help: "Help",
      team: "Team",
      invitations: "Invitations",
      audit: "Audit",
      privacy_operations: "Privacy Operations",
      integration_status: "Integration Status",
    },
    nav: {
      label: "Settings categories mobile",
      allCategories: "All settings categories",
      choose: "Choose one category to open its settings page.",
      workspace: "Workspace settings",
      administration: "Organization administration",
    },
    cards: {
      account: {
        description: "Your therapist workspace identity.",
        lines: [
          ["Name", "Demo Therapist"],
          ["Role", "Speech therapist / clinician"],
          ["Workspace start page", "Today"],
          ["Data mode", "Demo mode"],
        ],
      },
      organization: {
        description: "Your workspace and current data mode.",
        lines: [
          ["Organization", "Pilot organization workspace"],
          ["Data mode", "Demo mode"],
          ["Care team", "Read-only summaries appear only for authorized cases"],
          ["Administration", "Available only to organization admins"],
        ],
      },
      accessibility: {
        description: "Readable defaults for Thai–Latin clinical work and touch interaction.",
        lines: [
          ["Product font", "Noto Sans Thai / Noto Sans"],
          ["Accessibility mode", "Not enabled"],
          ["Motion", "Reduced motion follows your device preference"],
          ["Touch targets", "44 px minimum on touch devices"],
        ],
      },
      notifications: {
        description: "Notifications available in the pilot workspace.",
        lines: [
          ["In-app reminders", "Available"],
          ["Email delivery", "Not configured"],
          ["Caregiver messages", "Not configured"],
          ["Clinical content in alerts", "Not allowed"],
        ],
      },
      privacy: {
        description: "How access and session data are handled in the pilot workspace.",
        lines: [
          ["Authentication", "Demo workspace"],
          ["Credentials", "Managed by the current sign-in method"],
          ["Production MFA", "Not configured"],
          ["Session storage", "Browser UI cache only"],
        ],
      },
      export: {
        description: "Exports unlock after transcript review and sign-off.",
        lines: [
          ["Markdown export", "Configured after sign-off"],
          ["HTML export", "Configured after sign-off"],
          ["PDF export", "Not configured"],
          ["Caregiver share status", "Local/demo only"],
        ],
      },
      help: {
        description: "How the clinical workflow is meant to be used.",
        lines: [
          ["Transcript gate", "Quality attestation required"],
          ["Report export", "Sign-off required"],
          ["Clinical boundary", ""],
          ["Pilot workspace", "Anonymized demo data; no production accounts"],
        ],
      },
    },
    privacyRequests: {
      title: "Owned privacy requests",
      unavailable: "Unavailable in demo mode",
      body: "Production request history must come from a backend-confirmed authenticated identity; this screen does not infer an empty history.",
      noClaim: "No HIPAA compliance claim is made by this prototype workspace.",
    },
    signedIn: { fallbackName: "Workspace user", dataMode: "Signed-in workspace", authentication: "Supabase sign-in" },
  },
  th: {
    page: {
      title: "ตั้งค่า",
      description: "เลือกหมวดการตั้งค่าของพื้นที่ทำงาน ส่วนการดูแลองค์กรจะแสดงเฉพาะผู้ดูแลที่ได้รับสิทธิ์",
    },
    sections: {
      account: "บัญชี",
      organization: "องค์กร",
      accessibility: "การเข้าถึงและการแสดงผล",
      notifications: "การแจ้งเตือน",
      privacy: "ความเป็นส่วนตัวและความปลอดภัย",
      export: "การส่งออก",
      help: "ช่วยเหลือ",
      team: "ทีม",
      invitations: "คำเชิญ",
      audit: "บันทึกการตรวจสอบ",
      privacy_operations: "งานด้านความเป็นส่วนตัว",
      integration_status: "สถานะการเชื่อมต่อระบบ",
    },
    nav: {
      label: "หมวดการตั้งค่า",
      allCategories: "หมวดการตั้งค่าทั้งหมด",
      choose: "เลือกหมวดเพื่อเปิดหน้าการตั้งค่าของหมวดนั้น",
      workspace: "การตั้งค่าพื้นที่ทำงาน",
      administration: "การดูแลองค์กร",
    },
    cards: {
      account: {
        description: "ข้อมูลตัวตนของคุณในพื้นที่ทำงานของนักบำบัด",
        lines: [
          ["ชื่อ", "Demo Therapist"],
          ["บทบาท", "นักแก้ไขการพูด / นักบำบัด"],
          ["หน้าเริ่มต้น", "วันนี้"],
          ["โหมดข้อมูล", "โหมดสาธิต"],
        ],
      },
      organization: {
        description: "พื้นที่ทำงานของคุณและโหมดข้อมูลปัจจุบัน",
        lines: [
          ["องค์กร", "พื้นที่ทำงานขององค์กรนำร่อง"],
          ["โหมดข้อมูล", "โหมดสาธิต"],
          ["ทีมดูแล", "แสดงสรุปแบบดูได้อย่างเดียว เฉพาะเคสที่ได้รับสิทธิ์"],
          ["การดูแลระบบ", "ใช้ได้เฉพาะผู้ดูแลองค์กร"],
        ],
      },
      accessibility: {
        description: "ค่าเริ่มต้นที่อ่านง่ายสำหรับงานคลินิกภาษาไทยและอักษรละติน และการใช้งานแบบสัมผัส",
        lines: [
          ["ฟอนต์ของระบบ", "Noto Sans Thai / Noto Sans"],
          ["โหมดช่วยการเข้าถึง", "ยังไม่เปิดใช้"],
          ["การเคลื่อนไหว", "ลดการเคลื่อนไหวตามการตั้งค่าของอุปกรณ์"],
          ["ขนาดจุดสัมผัส", "อย่างน้อย 44 px บนอุปกรณ์สัมผัส"],
        ],
      },
      notifications: {
        description: "การแจ้งเตือนที่มีในพื้นที่ทำงานนำร่อง",
        lines: [
          ["การเตือนในแอป", "ใช้ได้"],
          ["การส่งอีเมล", "ยังไม่ได้ตั้งค่า"],
          ["ข้อความถึงผู้ดูแล", "ยังไม่ได้ตั้งค่า"],
          ["เนื้อหาทางคลินิกในการแจ้งเตือน", "ไม่อนุญาต"],
        ],
      },
      privacy: {
        description: "วิธีจัดการการเข้าถึงและข้อมูลเซสชันในพื้นที่ทำงานนำร่อง",
        lines: [
          ["การยืนยันตัวตน", "พื้นที่ทำงานสาธิต"],
          ["ข้อมูลเข้าสู่ระบบ", "จัดการโดยวิธีลงชื่อเข้าใช้ปัจจุบัน"],
          ["MFA สำหรับใช้งานจริง", "ยังไม่ได้ตั้งค่า"],
          ["ที่เก็บข้อมูลเซสชัน", "แคชของหน้าจอในเบราว์เซอร์เท่านั้น"],
        ],
      },
      export: {
        description: "ส่งออกได้หลังทบทวนบทถอดเสียงและลงนามแล้ว",
        lines: [
          ["ส่งออก Markdown", "ใช้ได้หลังลงนาม"],
          ["ส่งออก HTML", "ใช้ได้หลังลงนาม"],
          ["ส่งออก PDF", "ยังไม่ได้ตั้งค่า"],
          ["สถานะการแชร์กับผู้ดูแล", "เฉพาะในเครื่อง/สาธิต"],
        ],
      },
      help: {
        description: "แนวทางการใช้ขั้นตอนทางคลินิก",
        lines: [
          ["ด่านบทถอดเสียง", "ต้องรับรองคุณภาพก่อน"],
          ["การส่งออกรายงาน", "ต้องลงนามก่อน"],
          ["ขอบเขตทางคลินิก", ""],
          ["พื้นที่ทำงานนำร่อง", "ข้อมูลสาธิตที่ไม่ระบุตัวตน ไม่มีบัญชีใช้งานจริง"],
        ],
      },
    },
    privacyRequests: {
      title: "คำขอด้านความเป็นส่วนตัวของคุณ",
      unavailable: "ใช้ไม่ได้ในโหมดสาธิต",
      body: "ประวัติคำขอในการใช้งานจริงต้องมาจากตัวตนที่ระบบยืนยันแล้ว หน้านี้จะไม่สรุปเองว่าประวัติว่างเปล่า",
      noClaim: "พื้นที่ทำงานต้นแบบนี้ไม่ได้อ้างว่าเป็นไปตามข้อกำหนด HIPAA",
    },
    signedIn: { fallbackName: "ผู้ใช้พื้นที่ทำงาน", dataMode: "พื้นที่ทำงานที่ลงชื่อเข้าใช้", authentication: "ลงชื่อเข้าใช้ด้วย Supabase" },
  },
});
