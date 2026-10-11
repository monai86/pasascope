import { defineMessages } from "@/i18n/messages";

export const loginMessages = defineMessages({
  en: {
    productLine: "Clinical transcript workbench",
    prototypeChip: "Research and education prototype",
    hero: {
      eyebrow: "PasaScope · ภาษา-สโคป",
      title: "Review a child’s language sample, one clear step at a time",
      body: "Record or paste a session, correct the transcript, look at descriptive language measures, and sign a progress report. You decide at every step.",
      steps: [
        { title: "Transcribe and correct", body: "A draft transcript with child and adult turns, which you correct and attest." },
        { title: "Review descriptive measures", body: "Utterance length, vocabulary variety and turn-taking, with the utterances behind each cue." },
        { title: "Sign the report", body: "Nothing reaches a report until you have reviewed and signed it." },
      ],
    },
    footer: "PasaScope is a research and education prototype without Thai clinical validation.",
    panel: {
      loading: "Loading runtime settings…",
      unavailableTitle: "Runtime settings unavailable",
      unavailableBody: "Login is blocked until the application can confirm its authentication and access requirements.",
    },
    mock: {
      formLabel: "Mock login form",
      title: "Mock login",
      description: "Therapist, supervisor, and org-admin demo roles are available for local exploration.",
      email: "Email",
      role: "Role",
      roles: { therapist: "Therapist", clinical_supervisor: "Clinical supervisor", org_admin: "Org admin" },
      organization: "Active organization session",
      assurance: "Session assurance",
      destination: {
        therapist: "Therapist opens Today.",
        clinical_supervisor: "Clinical supervisor opens the work queue with org-wide oversight.",
        org_admin: "Org admin opens assignment-safe runtime controls.",
      },
      organizationNote: {
        title: "Organization session selection",
        multiple: "This mock role simulates multiple memberships, so the active organization must be selected explicitly before workspace access.",
        single: "This mock role has a single organization membership, so the active organization is preselected.",
        aalBefore: "Selecting ",
        aalMiddle: " will stop at the MFA gate until the session is promoted to ",
        aalAfter: ".",
      },
      boundary: {
        title: "Production access boundary",
        open: "Runtime settings do not currently enforce invitation-only onboarding.",
        invitationOnly: "Production access stays invitation-only and requires AAL2 before app access.",
        localOnly: "Mock mode is for local exploration only and does not provision real clinic accounts or real organization sessions.",
      },
      submit: "Enter workspace",
    },
  },
  th: {
    productLine: "พื้นที่ทำงานสำหรับทบทวนบทถอดเสียงทางคลินิก",
    prototypeChip: "ต้นแบบเพื่อการวิจัยและการศึกษา",
    hero: {
      eyebrow: "PasaScope · ภาษา-สโคป",
      title: "ทบทวนตัวอย่างภาษาของเด็กทีละขั้นอย่างชัดเจน",
      body: "บันทึกเสียงหรือวางบทสนทนา แก้ไขบทถอดเสียง ดูค่าพรรณนาทางภาษา แล้วลงนามรายงานความก้าวหน้า โดยคุณเป็นผู้ตัดสินใจในทุกขั้นตอน",
      steps: [
        { title: "ถอดเสียงและแก้ไข", body: "ร่างบทถอดเสียงแยกผู้พูดเป็นเด็กและผู้ใหญ่ ให้คุณแก้ไขและรับรอง" },
        { title: "ทบทวนค่าพรรณนา", body: "ความยาวถ้อยคำ ความหลากหลายของคำศัพท์ และการผลัดกันพูด พร้อมถ้อยคำที่เป็นที่มาของแต่ละข้อสังเกต" },
        { title: "ลงนามรายงาน", body: "ไม่มีข้อมูลใดเข้าสู่รายงานจนกว่าคุณจะทบทวนและลงนาม" },
      ],
    },
    footer: "PasaScope เป็นต้นแบบเพื่อการวิจัยและการศึกษา ยังไม่ผ่านการตรวจสอบความตรงทางคลินิกในประเทศไทย",
    panel: {
      loading: "กำลังโหลดการตั้งค่าระบบ…",
      unavailableTitle: "ไม่สามารถอ่านการตั้งค่าระบบได้",
      unavailableBody: "ยังลงชื่อเข้าใช้ไม่ได้จนกว่าระบบจะยืนยันวิธีลงชื่อเข้าใช้และสิทธิ์การเข้าถึงได้",
    },
    mock: {
      formLabel: "แบบฟอร์มลงชื่อเข้าใช้จำลอง",
      title: "ลงชื่อเข้าใช้จำลอง",
      description: "มีบทบาทนักบำบัด ผู้นิเทศ และผู้ดูแลองค์กรให้ทดลองใช้บนเครื่องนี้",
      email: "อีเมล",
      role: "บทบาท",
      roles: { therapist: "นักบำบัด", clinical_supervisor: "ผู้นิเทศทางคลินิก", org_admin: "ผู้ดูแลองค์กร" },
      organization: "องค์กรที่ใช้งานในเซสชันนี้",
      assurance: "ระดับการยืนยันตัวตน",
      destination: {
        therapist: "นักบำบัดจะเข้าสู่หน้าวันนี้",
        clinical_supervisor: "ผู้นิเทศทางคลินิกจะเข้าสู่คิวงานที่เห็นภาพรวมทั้งองค์กร",
        org_admin: "ผู้ดูแลองค์กรจะเข้าสู่หน้าตั้งค่าการมอบหมายงาน",
      },
      organizationNote: {
        title: "การเลือกองค์กรของเซสชัน",
        multiple: "บทบาทจำลองนี้เป็นสมาชิกหลายองค์กร จึงต้องเลือกองค์กรที่ใช้งานให้ชัดเจนก่อนเข้าพื้นที่ทำงาน",
        single: "บทบาทจำลองนี้เป็นสมาชิกองค์กรเดียว ระบบจึงเลือกองค์กรให้แล้ว",
        aalBefore: "หากเลือก ",
        aalMiddle: " ระบบจะหยุดที่ขั้นยืนยันตัวตนสองชั้น จนกว่าเซสชันจะยกระดับเป็น ",
        aalAfter: "",
      },
      boundary: {
        title: "ขอบเขตการเข้าถึงในระบบจริง",
        open: "การตั้งค่าปัจจุบันยังไม่ได้บังคับให้เข้าใช้ด้วยคำเชิญเท่านั้น",
        invitationOnly: "ระบบจริงเข้าใช้ได้ด้วยคำเชิญเท่านั้น และต้องยืนยันตัวตนระดับ AAL2 ก่อนเข้าแอป",
        localOnly: "โหมดจำลองใช้สำรวจบนเครื่องนี้เท่านั้น ไม่ได้สร้างบัญชีคลินิกหรือเซสชันองค์กรจริง",
      },
      submit: "เข้าสู่พื้นที่ทำงาน",
    },
  },
});
