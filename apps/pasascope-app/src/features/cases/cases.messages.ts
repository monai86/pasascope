import { defineMessages } from "@/i18n/messages";

export type CaseStage = "consent" | "transcript" | "signOff" | "drafting" | "session" | "intake";
export type CaseNextAction = "reviewConsent" | "reviewSession" | "finalizeReport" | "continueWorkflow" | "startSession";

type CasesCopy = {
  shared: {
    ageNotRecorded: string;
    age: (years: number, months: number) => string;
    languageNotRecorded: string;
    notAssigned: string;
    noClinicianAssigned: string;
    stages: Record<CaseStage, string>;
    consentStates: Record<string, string>;
    consentUnknown: string;
    notStarted: string;
    verifyConsent: string;
  };
  workspace: {
    loading: string;
    unavailableTitle: string;
    unavailableBody: string;
    errorTitle: string;
    errorBody: string;
    retry: string;
    backToCases: string;
  };
  list: {
    title: string;
    description: string;
    closeForm: string;
    createCase: string;
    searchLabel: string;
    searchPlaceholder: string;
    clinicianFilter: string;
    allClinicians: string;
    statusFilters: string;
    allStatuses: string;
    consentFilter: string;
    allConsent: string;
    consentActive: string;
    consentPending: string;
    consentWithdrawn: string;
    sort: string;
    /** The word shown beside the sort control; `sort` is its full accessible name. */
    sortShort: string;
    sortLatest: string;
    sortNext: string;
    tableCaption: string;
    columns: { case: string; latestActivity: string; workflowStatus: string; nextAction: string };
    noActivity: string;
    listLabel: string;
    actions: Record<CaseNextAction, string>;
    emptyTitle: string;
    emptyCanCreate: string;
    emptyCannotCreate: string;
    createFirst: string;
    noMatchTitle: string;
    noMatchBody: string;
    clearFilters: string;
    showing: (shown: number, total: number) => string;
    /** Shown beside a case that review has marked as urgent; other priorities are not listed. */
    highPriority: string;
  };
  detail: {
    withdrawTitle: string;
    withdrawBody: string;
    withdrawConfirm: string;
    withdrawCancel: string;
    /** Offered on a case with nothing recorded for it, such as one created by mistake. */
    remove: { hint: string; action: string; title: string; body: string; confirm: string; cancel: string; failed: string };
    description: string;
    caseCode: (code: string) => string;
    createSession: string;
    profile: string;
    caseStatus: string;
    primaryTherapist: string;
    consentStatus: string;
    latestSession: string;
    consentRequiredTitle: string;
    consentRequiredBody: string;
    consentFormTitle: string;
    consentFormBody: string;
    consentActive: string;
    consentActiveBody: string;
    withdraw: string;
    overview: string;
    childLabel: string;
    age: string;
    language: string;
    referral: string;
    referralEmpty: string;
    careTeam: string;
    primaryClinician: string;
    assignedClinicians: string;
    careTeamNote: string;
    goals: string;
    goalTargetEmpty: string;
    goalsEmpty: string;
    sessions: string;
    sessionsEmpty: string;
    languageProgress: string;
    reports: string;
    reportNote: (signOffClause: string) => string;
    openReports: string;
    upcomingTasks: string;
    tasks: { consent: string; review: string; fallback: string };
    recentNotes: string;
    notesEmpty: string;
    safetyNote: string;
    progress: string;
    workflowStage: string;
    reportStatus: string;
    historyCaption: string;
    historyColumns: { session: string; date: string; status: string; nextAction: string };
    openSession: string;
    showFewer: string;
    showAll: (count: number) => string;
  };
  create: {
    title: string;
    body: string;
    caseCode: string;
    nickname: string;
    nicknameHint: string;
    ageMonths: string;
    language: string;
    notes: string;
    notesHint: string;
    failed: string;
    saving: string;
    save: string;
    cancel: string;
  };
  start: {
    title: string;
    description: string;
    meta: string;
    backToCases: string;
    available: string;
    availableNote: string;
    preselected: (code: string) => string;
    noneTitle: string;
    noneBody: string;
    listLabel: string;
    consentActive: string;
    consentRequired: string;
    creating: string;
    creatingButton: string;
    startFor: (code: string) => string;
    start: string;
    failed: string;
    safetyNote: string;
  };
};

export const casesMessages = defineMessages<CasesCopy>({
  en: {
    shared: {
      ageNotRecorded: "Age not recorded",
      age: (years, months) => `${years}y ${months}m`,
      languageNotRecorded: "Language not recorded",
      notAssigned: "Not assigned",
      noClinicianAssigned: "No clinician assigned",
      stages: {
        consent: "Consent follow-up",
        transcript: "Transcript review",
        signOff: "Report sign-off",
        drafting: "Report drafting",
        session: "Session in progress",
        intake: "Intake ready",
      },
      consentStates: { granted: "Granted", pending: "Pending", withdrawn: "Withdrawn" },
      consentUnknown: "Unknown",
      notStarted: "Not started",
      verifyConsent: "Verify and Grant Consent",
    },
    workspace: {
      loading: "Loading cases…",
      unavailableTitle: "Cases are unavailable",
      unavailableBody: "The backend cases service could not be reached. Try again when the service is available.",
      errorTitle: "Case could not be loaded",
      errorBody: "The requested backend case was not returned. Check the case link or try again.",
      retry: "Try again",
      backToCases: "Back to Cases",
    },
    list: {
      title: "Cases",
      description: "Find a case and take its next step.",
      closeForm: "Close form",
      createCase: "Create case",
      searchLabel: "Search cases",
      searchPlaceholder: "Search by child label, case code, language, or clinician",
      clinicianFilter: "Clinician filter",
      allClinicians: "All clinicians",
      statusFilters: "Status filters",
      allStatuses: "All statuses",
      consentFilter: "Consent filter",
      allConsent: "All consent states",
      consentActive: "Consent active",
      consentPending: "Consent pending",
      consentWithdrawn: "Consent withdrawn",
      sort: "Sort cases",
      sortShort: "Sort",
      sortLatest: "Latest activity",
      sortNext: "Next action",
      tableCaption: "Cases workspace",
      columns: { case: "Case", latestActivity: "Latest activity", workflowStatus: "Workflow status", nextAction: "Next action" },
      noActivity: "No session activity yet",
      listLabel: "Cases",
      actions: {
        reviewConsent: "Review consent",
        reviewSession: "Review session",
        finalizeReport: "Finalize report",
        continueWorkflow: "Continue workflow",
        startSession: "Start session",
      },
      emptyTitle: "No cases yet",
      emptyCanCreate: "Create a de-identified case before recording consent or starting a session.",
      emptyCannotCreate: "Ask an assigned therapist to create a de-identified case before starting a session.",
      createFirst: "Create the first case",
      noMatchTitle: "No cases match these filters",
      noMatchBody: "Change the search text or filters, or clear them to see every case.",
      clearFilters: "Clear filters",
      showing: (shown, total) => `Showing ${shown ? `1-${shown}` : "0-0"} of ${total} cases`,
      highPriority: "High priority",
    },
    detail: {
      withdrawTitle: "Withdraw consent for this case?",
      withdrawBody:
        "This will redact child details and disable clinical workflows for this case. New sessions stay blocked until consent is granted again.",
      withdrawConfirm: "Withdraw consent",
      withdrawCancel: "Keep consent",
      remove: {
        hint: "This case has no sessions. If it was created by mistake, it can be deleted.",
        action: "Delete case",
        title: "Delete this case?",
        body: "The case is removed from your list. It cannot be brought back.",
        confirm: "Delete case",
        cancel: "Keep case",
        failed: "The case could not be deleted. It may have records now; reload the page and check.",
      },
      description: "Use the persisted case record to review workflow progress, referral context, and therapist-owned next steps.",
      caseCode: (code) => `Case ${code}`,
      createSession: "Create new session",
      profile: "Case profile",
      caseStatus: "Case status",
      primaryTherapist: "Primary therapist",
      consentStatus: "Consent status",
      latestSession: "Latest session",
      consentRequiredTitle: "Caregiver Consent Verification Required",
      consentRequiredBody:
        "This case requires verified caregiver consent. Session recording, audio processing, and clinical observation workflows are locked until consent is obtained and verified.",
      consentFormTitle: "Consent Verification Form",
      consentFormBody: "Please verify consent credentials below to unlock the clinical intake and session workflows.",
      consentActive: "Consent Active",
      consentActiveBody: "Caregiver consent has been verified and clinical workflows are unlocked.",
      withdraw: "Withdraw Consent",
      overview: "Overview",
      childLabel: "Child label",
      age: "Age",
      language: "Language",
      referral: "Referral/context",
      referralEmpty: "Referral or intake context has not been added yet.",
      careTeam: "Care team",
      primaryClinician: "Primary clinician",
      assignedClinicians: "Assigned clinicians",
      careTeamNote:
        "This is a read-only care-team summary. Organization administrators manage assignments in the role-gated Team section of Settings.",
      goals: "Goals",
      goalTargetEmpty: "Target not yet documented.",
      goalsEmpty: "No communication goals recorded yet.",
      sessions: "Sessions",
      sessionsEmpty: "No sessions recorded yet for this case.",
      languageProgress: "Language progress",
      reports: "Reports",
      reportNote: (signOffClause) => `Report status reflects backend workflow state. ${signOffClause} before export.`,
      openReports: "Open Reports",
      upcomingTasks: "Upcoming tasks",
      tasks: {
        consent: "Confirm consent status before creating or reopening sessions.",
        review: "Review the latest session transcript before downstream workflow steps.",
        fallback: "Open the latest session workspace and confirm the next therapist-reviewed step.",
      },
      recentNotes: "Recent notes",
      notesEmpty: "No recent therapist notes recorded yet.",
      safetyNote: "Case detail is a workflow summary and referral/context record. It does not display diagnostic conclusions.",
      progress: "Progress",
      workflowStage: "Workflow stage",
      reportStatus: "Report status",
      historyCaption: "Case session history",
      historyColumns: { session: "Session", date: "Date", status: "Status", nextAction: "Next action" },
      openSession: "Open session workspace",
      showFewer: "Show fewer sessions",
      showAll: (count) => `Show all sessions (${count})`,
    },
    create: {
      title: "Create a de-identified case",
      body: "Use a study or clinic code, not a child's name or direct identifier. Consent starts as pending.",
      caseCode: "Case code",
      nickname: "Nickname",
      nicknameHint: "Optional and de-identified",
      ageMonths: "Age in months",
      language: "Language",
      notes: "Case notes",
      notesHint: "Optional; do not enter direct identifiers",
      failed: "The case could not be created. Check the details and try again.",
      saving: "Saving case…",
      save: "Save case",
      cancel: "Cancel",
    },
    start: {
      title: "Choose a case to start a session",
      description: "Select one consented case. PasaScope creates the session on the backend before opening Intake.",
      meta: "No session is created until you confirm",
      backToCases: "Back to Cases",
      available: "Available cases",
      availableNote: "Cases without active consent remain visible for context but cannot be selected.",
      preselected: (code) =>
        `Case ${code} was preselected from the previous screen. You can still choose another consented case.`,
      noneTitle: "No consented cases available",
      noneBody: "Confirm consent from the case record before starting a session.",
      listLabel: "Cases available for a new session",
      consentActive: "Consent active",
      consentRequired: "Consent required",
      creating: "Creating the session…",
      creatingButton: "Creating session…",
      startFor: (code) => `Start session for ${code}`,
      start: "Start session",
      failed: "The session could not be created. Please retry.",
      safetyNote: "Starting a session does not generate findings or a report.",
    },
  },
  th: {
    shared: {
      ageNotRecorded: "ไม่ได้บันทึกอายุ",
      age: (years, months) => `${years} ปี ${months} เดือน`,
      languageNotRecorded: "ไม่ได้บันทึกภาษา",
      notAssigned: "ยังไม่ได้มอบหมาย",
      noClinicianAssigned: "ยังไม่มีนักบำบัดที่ได้รับมอบหมาย",
      stages: {
        consent: "ติดตามความยินยอม",
        transcript: "ทบทวนบทถอดเสียง",
        signOff: "ลงนามรายงาน",
        drafting: "ร่างรายงาน",
        session: "เซสชันกำลังดำเนินการ",
        intake: "พร้อมรับข้อมูล",
      },
      consentStates: { granted: "ให้ความยินยอมแล้ว", pending: "รอความยินยอม", withdrawn: "ถอนความยินยอมแล้ว" },
      consentUnknown: "ไม่ทราบ",
      notStarted: "ยังไม่เริ่ม",
      verifyConsent: "ยืนยันและบันทึกความยินยอม",
    },
    workspace: {
      loading: "กำลังโหลดเคส…",
      unavailableTitle: "ยังเปิดดูเคสไม่ได้",
      unavailableBody: "ติดต่อบริการข้อมูลเคสไม่ได้ ลองใหม่เมื่อบริการกลับมาใช้ได้",
      errorTitle: "โหลดเคสไม่ได้",
      errorBody: "ระบบไม่ส่งข้อมูลเคสที่ขอกลับมา ตรวจลิงก์ของเคสหรือลองอีกครั้ง",
      retry: "ลองอีกครั้ง",
      backToCases: "กลับไปหน้าเคส",
    },
    list: {
      title: "เคส",
      description: "ค้นหาเคส แล้วทำขั้นถัดไปของเคสนั้น",
      closeForm: "ปิดแบบฟอร์ม",
      createCase: "สร้างเคส",
      searchLabel: "ค้นหาเคส",
      searchPlaceholder: "ค้นด้วยชื่อเรียกเด็ก รหัสเคส ภาษา หรือนักบำบัด",
      clinicianFilter: "กรองตามนักบำบัด",
      allClinicians: "นักบำบัดทุกคน",
      statusFilters: "กรองตามสถานะ",
      allStatuses: "ทุกสถานะ",
      consentFilter: "กรองตามความยินยอม",
      allConsent: "ทุกสถานะความยินยอม",
      consentActive: "ให้ความยินยอมแล้ว",
      consentPending: "รอความยินยอม",
      consentWithdrawn: "ถอนความยินยอมแล้ว",
      sort: "เรียงเคส",
      sortShort: "เรียง",
      sortLatest: "ความเคลื่อนไหวล่าสุด",
      sortNext: "งานถัดไป",
      tableCaption: "รายการเคส",
      columns: { case: "เคส", latestActivity: "ความเคลื่อนไหวล่าสุด", workflowStatus: "สถานะงาน", nextAction: "งานถัดไป" },
      noActivity: "ยังไม่มีเซสชัน",
      listLabel: "เคส",
      actions: {
        reviewConsent: "ตรวจความยินยอม",
        reviewSession: "ทบทวนเซสชัน",
        finalizeReport: "ลงนามรายงาน",
        continueWorkflow: "ทำต่อ",
        startSession: "เริ่มเซสชัน",
      },
      emptyTitle: "ยังไม่มีเคส",
      emptyCanCreate: "สร้างเคสที่ไม่ระบุตัวตนก่อนบันทึกความยินยอมหรือเริ่มเซสชัน",
      emptyCannotCreate: "ขอให้นักบำบัดที่ได้รับมอบหมายสร้างเคสที่ไม่ระบุตัวตนก่อนเริ่มเซสชัน",
      createFirst: "สร้างเคสแรก",
      noMatchTitle: "ไม่มีเคสที่ตรงกับตัวกรอง",
      noMatchBody: "เปลี่ยนคำค้นหรือตัวกรอง หรือล้างตัวกรองเพื่อดูเคสทั้งหมด",
      clearFilters: "ล้างตัวกรอง",
      showing: (shown, total) => `แสดง ${shown ? `1-${shown}` : "0"} จาก ${total} เคส`,
      highPriority: "ลำดับความสำคัญสูง",
    },
    detail: {
      withdrawTitle: "ถอนความยินยอมของเคสนี้ใช่ไหม",
      withdrawBody:
        "ระบบจะปิดบังรายละเอียดของเด็กและปิดขั้นตอนทางคลินิกของเคสนี้ เซสชันใหม่จะเริ่มไม่ได้จนกว่าจะได้รับความยินยอมอีกครั้ง",
      withdrawConfirm: "ถอนความยินยอม",
      withdrawCancel: "คงความยินยอมไว้",
      remove: {
        hint: "เคสนี้ยังไม่มีเซสชัน ถ้าสร้างผิด ลบได้",
        action: "ลบเคส",
        title: "ลบเคสนี้ใช่ไหม",
        body: "เคสจะหายจากรายการของคุณ และกู้คืนไม่ได้",
        confirm: "ลบเคส",
        cancel: "เก็บเคสไว้",
        failed: "ลบเคสไม่สำเร็จ เคสอาจมีข้อมูลแล้ว ลองโหลดหน้าใหม่แล้วตรวจอีกครั้ง",
      },
      description: "ดูความคืบหน้าของงาน บริบทการส่งต่อ และขั้นถัดไปของนักบำบัด จากข้อมูลเคสที่บันทึกไว้",
      caseCode: (code) => `เคส ${code}`,
      createSession: "สร้างเซสชันใหม่",
      profile: "ข้อมูลเคส",
      caseStatus: "สถานะเคส",
      primaryTherapist: "นักบำบัดหลัก",
      consentStatus: "สถานะความยินยอม",
      latestSession: "เซสชันล่าสุด",
      consentRequiredTitle: "ต้องยืนยันความยินยอมของผู้ดูแลก่อน",
      consentRequiredBody:
        "เคสนี้ต้องมีความยินยอมของผู้ดูแลที่ยืนยันแล้ว การบันทึกเซสชัน การประมวลผลเสียง และขั้นตอนข้อสังเกตทางคลินิกจะล็อกอยู่จนกว่าจะได้รับและยืนยันความยินยอม",
      consentFormTitle: "แบบฟอร์มยืนยันความยินยอม",
      consentFormBody: "ยืนยันข้อมูลความยินยอมด้านล่าง เพื่อปลดล็อกการรับข้อมูลและขั้นตอนของเซสชัน",
      consentActive: "ให้ความยินยอมแล้ว",
      consentActiveBody: "ยืนยันความยินยอมของผู้ดูแลแล้ว ขั้นตอนทางคลินิกใช้งานได้",
      withdraw: "ถอนความยินยอม",
      overview: "ภาพรวม",
      childLabel: "ชื่อเรียกเด็ก",
      age: "อายุ",
      language: "ภาษา",
      referral: "การส่งต่อ/บริบท",
      referralEmpty: "ยังไม่ได้เพิ่มข้อมูลการส่งต่อหรือบริบทการรับเข้า",
      careTeam: "ทีมดูแล",
      primaryClinician: "นักบำบัดหลัก",
      assignedClinicians: "นักบำบัดที่ได้รับมอบหมาย",
      careTeamNote: "ส่วนนี้ดูได้อย่างเดียว ผู้ดูแลองค์กรจัดการการมอบหมายได้ที่ส่วนทีมในหน้าตั้งค่า",
      goals: "เป้าหมาย",
      goalTargetEmpty: "ยังไม่ได้บันทึกเป้าที่ต้องการ",
      goalsEmpty: "ยังไม่มีเป้าหมายด้านการสื่อสารที่บันทึกไว้",
      sessions: "เซสชัน",
      sessionsEmpty: "เคสนี้ยังไม่มีเซสชันที่บันทึกไว้",
      languageProgress: "ความก้าวหน้าทางภาษา",
      reports: "รายงาน",
      reportNote: (signOffClause) => `สถานะรายงานมาจากสถานะงานในระบบ ${signOffClause}ก่อนส่งออก`,
      openReports: "เปิดหน้ารายงาน",
      upcomingTasks: "งานที่ต้องทำ",
      tasks: {
        consent: "ยืนยันสถานะความยินยอมก่อนสร้างหรือเปิดเซสชันอีกครั้ง",
        review: "ทบทวนบทถอดเสียงของเซสชันล่าสุดก่อนทำขั้นถัดไป",
        fallback: "เปิดเซสชันล่าสุด แล้วยืนยันขั้นถัดไปที่นักบำบัดต้องทบทวน",
      },
      recentNotes: "บันทึกล่าสุด",
      notesEmpty: "ยังไม่มีบันทึกของนักบำบัด",
      safetyNote: "หน้ารายละเอียดเคสเป็นสรุปงานและบันทึกการส่งต่อ/บริบท ไม่แสดงข้อสรุปเชิงวินิจฉัย",
      progress: "ความคืบหน้า",
      workflowStage: "ขั้นของงาน",
      reportStatus: "สถานะรายงาน",
      historyCaption: "ประวัติเซสชันของเคส",
      historyColumns: { session: "เซสชัน", date: "วันที่", status: "สถานะ", nextAction: "งานถัดไป" },
      openSession: "เปิดเซสชัน",
      showFewer: "แสดงเซสชันน้อยลง",
      showAll: (count) => `แสดงเซสชันทั้งหมด (${count})`,
    },
    create: {
      title: "สร้างเคสที่ไม่ระบุตัวตน",
      body: "ใช้รหัสของงานวิจัยหรือคลินิก ไม่ใช้ชื่อเด็กหรือข้อมูลที่ระบุตัวตนโดยตรง ความยินยอมเริ่มต้นที่สถานะรอ",
      caseCode: "รหัสเคส",
      nickname: "ชื่อเรียก",
      nicknameHint: "ไม่บังคับ และต้องไม่ระบุตัวตน",
      ageMonths: "อายุ (เดือน)",
      language: "ภาษา",
      notes: "บันทึกของเคส",
      notesHint: "ไม่บังคับ ห้ามใส่ข้อมูลที่ระบุตัวตนโดยตรง",
      failed: "สร้างเคสไม่ได้ ตรวจรายละเอียดแล้วลองอีกครั้ง",
      saving: "กำลังบันทึกเคส…",
      save: "บันทึกเคส",
      cancel: "ยกเลิก",
    },
    start: {
      title: "เลือกเคสเพื่อเริ่มเซสชัน",
      description: "เลือกเคสที่ให้ความยินยอมแล้วหนึ่งเคส PasaScope จะสร้างเซสชันในระบบก่อนเปิดหน้ารับข้อมูล",
      meta: "ยังไม่สร้างเซสชันจนกว่าคุณจะยืนยัน",
      backToCases: "กลับไปหน้าเคส",
      available: "เคสที่เลือกได้",
      availableNote: "เคสที่ยังไม่มีความยินยอมจะแสดงไว้ให้เห็น แต่เลือกไม่ได้",
      preselected: (code) => `เลือกเคส ${code} ไว้ให้จากหน้าก่อนหน้า คุณยังเลือกเคสอื่นที่ให้ความยินยอมแล้วได้`,
      noneTitle: "ไม่มีเคสที่ให้ความยินยอมแล้ว",
      noneBody: "ยืนยันความยินยอมจากหน้าข้อมูลเคสก่อนเริ่มเซสชัน",
      listLabel: "เคสที่เริ่มเซสชันใหม่ได้",
      consentActive: "ให้ความยินยอมแล้ว",
      consentRequired: "ต้องมีความยินยอม",
      creating: "กำลังสร้างเซสชัน…",
      creatingButton: "กำลังสร้างเซสชัน…",
      startFor: (code) => `เริ่มเซสชันของ ${code}`,
      start: "เริ่มเซสชัน",
      failed: "สร้างเซสชันไม่ได้ ลองอีกครั้ง",
      safetyNote: "การเริ่มเซสชันไม่ได้สร้างผลการวิเคราะห์หรือรายงาน",
    },
  },
});
