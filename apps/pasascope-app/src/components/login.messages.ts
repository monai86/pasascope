import { defineMessages } from "@/i18n/messages";

export const loginMessages = defineMessages({
  en: {
    productLine: "Clinical transcript workbench",
    hero: {
      // Broken by phrase, as the Thai title is.
      title: "From a child’s voice\nto a report draft,\nstep by step",
      body: "Send a session’s audio and PasaScope takes you through the rest. You decide at every step.",
      steps: [
        { title: "Send the audio", body: "Record the session here, or upload a file you already have." },
        { title: "Check the transcript", body: "Correct the text and say who spoke each line." },
        { title: "Measures and report", body: "See descriptive language measures and a report draft you can edit." },
      ],
    },
    footer: "PasaScope is a research and education prototype without Thai clinical validation.",
    panel: {
      loading: "Getting sign-in ready…",
      waking: "The service is starting up. This can take about a minute.",
      unavailableTitle: "Runtime settings unavailable",
      unavailableBody: "Sign-in could not be prepared. Try again in a moment.",
      retry: "Try again",
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
    hero: {
      // The break keeps each phrase whole; Thai has no spaces for the browser to balance on.
      title: "จากเสียงของเด็ก\nถึงร่างรายงาน ทีละขั้น",
      body: "ส่งเสียงของเซสชันมา แล้ว PasaScope จะพาทำขั้นที่เหลือ โดยคุณเป็นผู้ตัดสินใจทุกขั้น",
      steps: [
        { title: "ส่งเสียง", body: "อัดเสียงเซสชันที่นี่ หรืออัปโหลดไฟล์ที่มีอยู่" },
        { title: "ตรวจบทถอดเสียง", body: "แก้ข้อความ และกำหนดว่าใครพูดแต่ละบรรทัด" },
        { title: "ค่าทางภาษาและรายงาน", body: "ดูค่าพรรณนาทางภาษา และร่างรายงานที่คุณแก้ไขได้" },
      ],
    },
    footer: "PasaScope เป็นต้นแบบเพื่อการวิจัยและการศึกษา ยังไม่ผ่านการตรวจสอบความตรงทางคลินิกในประเทศไทย",
    panel: {
      loading: "กำลังเตรียมหน้าลงชื่อเข้าใช้…",
      waking: "ระบบกำลังเริ่มทำงาน อาจใช้เวลาประมาณหนึ่งนาที",
      unavailableTitle: "ยังเตรียมหน้าลงชื่อเข้าใช้ไม่ได้",
      unavailableBody: "เตรียมหน้าลงชื่อเข้าใช้ไม่สำเร็จ ลองใหม่อีกครั้งในอีกสักครู่",
      retry: "ลองอีกครั้ง",
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
