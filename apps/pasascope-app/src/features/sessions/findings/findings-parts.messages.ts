import { defineMessages } from "@/i18n/messages";

type GroupId = "language-sample" | "lexical-use" | "interaction" | "speech-intelligibility" | "data-quality";

type FindingsPartsCopy = {
  progress: { title: string; body: string; chip: string; generating: string; generate: string };
  grid: {
    title: string;
    body: string;
    signals: (count: number) => string;
    groups: Record<GroupId, { label: string; caution: string }>;
    hide: string;
    show: string;
    method: string;
    limitations: string;
    caution: string;
    emptyGroup: string;
    footer: string;
  };
  evidence: {
    summary: string;
    reviewPoints: (count: number) => string;
    recommended: string;
    providerLine: (name: string, version: string, schema: string) => string;
    notComputed: string;
    adult: string;
    child: string;
    lineGone: string;
    repeatsWhole: string;
    repeatsPart: string;
    next: (step: string) => string;
    confirm: string;
    dismiss: string;
    confirmed: string;
    dismissed: string;
    notReviewed: string;
    openTranscript: string;
    profile: (code: string) => string;
    presentationGroup: (group: string) => string;
    referenceSupport: (participants: number, corpora: number) => string;
    observed: (value: string, position: string) => string;
    distribution: (q1: string, median: string, q3: string) => string;
    reviewed: string;
    recordDisagreement: string;
    disagreementNote: string;
    disagreementLabel: (code: string) => string;
    saveDisagreement: string;
    cancel: string;
    hideEvidence: string;
    viewEvidence: string;
  };
  availability: { canContinue: string; actionRequired: string; next: (step: string) => string };
};

export const findingsPartsMessages = defineMessages<FindingsPartsCopy>({
  en: {
    progress: {
      title: "Progress Summary",
      body: "AI-assisted longitudinal context for this case, including the typical-development reference band when available.",
      chip: "AI-assisted review",
      generating: "Generating...",
      generate: "Generate AI-assisted review",
    },
    grid: {
      title: "Language sample at a glance",
      body: "Every extracted value from this reviewed sample, grouped for quick comparison.",
      signals: (count) => `${count} signals`,
      groups: {
        "language-sample": { label: "Language sample", caution: "Interpret alongside sample length and elicitation context." },
        "lexical-use": { label: "Lexical use", caution: "Vocabulary cues depend on the reviewed transcript sample." },
        interaction: { label: "Interaction", caution: "Review with speaker roles and interaction context." },
        "speech-intelligibility": {
          label: "Speech / intelligibility",
          caution: "Transcript cues are not a substitute for direct speech assessment.",
        },
        "data-quality": { label: "Data quality", caution: "Resolve material data-quality concerns before report use." },
      },
      hide: "Hide evidence and limitations",
      show: "Evidence and limitations",
      method: "Method",
      limitations: "Limitations",
      caution: "Clinical interpretation caution",
      emptyGroup: "No features from this group in this session.",
      footer: "Values are descriptive cues from the reviewed transcript, not diagnostic results. Compare them with therapist context.",
    },
    evidence: {
      summary: "Review guidance and evidence",
      reviewPoints: (count) => `${count} review point${count === 1 ? "" : "s"}`,
      recommended: "Recommended review points",
      providerLine: (name, version, schema) => `${name} v${version} · schema ${schema}`,
      notComputed: "not computed",
      adult: "Adult:",
      child: "Child:",
      lineGone: "(line no longer in transcript)",
      repeatsWhole: "Repeats the adult turn",
      repeatsPart: "Repeats part of the adult turn",
      next: (step) => `Next: ${step}`,
      confirm: "Confirm after checking",
      dismiss: "Dismiss — not an echo or pronoun issue",
      confirmed: "Confirmed by therapist",
      dismissed: "Dismissed by therapist",
      notReviewed: "Not yet reviewed",
      openTranscript: "Open transcript",
      profile: (code) => `${code} profile`,
      presentationGroup: (group) => `Presentation group: ${group}`,
      referenceSupport: (participants, corpora) => `Reference support: ${participants} participants · ${corpora} corpora`,
      observed: (value, position) => `Observed ${value} · ${position}`,
      distribution: (q1, median, q3) => `Reference distribution Q1 ${q1} · median ${median} · Q3 ${q3}`,
      reviewed: "Reviewed",
      recordDisagreement: "Record disagreement",
      disagreementNote: "This records clinical disagreement and preserves the original provider output.",
      disagreementLabel: (code) => `Disagreement note for ${code}`,
      saveDisagreement: "Save disagreement",
      cancel: "Cancel",
      hideEvidence: "Hide supporting evidence",
      viewEvidence: "View supporting evidence",
    },
    availability: {
      canContinue: "Feature and report workflow can continue.",
      actionRequired: "Workflow action is required before continuing.",
      next: (step) => `Next: ${step}`,
    },
  },
  th: {
    progress: {
      title: "สรุปความก้าวหน้า",
      body: "บริบทตามช่วงเวลาของเคสนี้ที่ AI ช่วยเรียบเรียง รวมช่วงอ้างอิงของพัฒนาการทั่วไปเมื่อมีข้อมูล",
      chip: "การทบทวนโดยมี AI ช่วย",
      generating: "กำลังสร้าง...",
      generate: "สร้างการทบทวนโดยมี AI ช่วย",
    },
    grid: {
      title: "ภาพรวมของตัวอย่างภาษา",
      body: "ค่าทั้งหมดที่สกัดจากตัวอย่างที่ทบทวนแล้ว จัดกลุ่มไว้ให้เทียบได้เร็ว",
      signals: (count) => `${count} ค่า`,
      groups: {
        "language-sample": { label: "ตัวอย่างภาษา", caution: "ตีความร่วมกับความยาวของตัวอย่างและบริบทการเก็บตัวอย่าง" },
        "lexical-use": { label: "การใช้คำศัพท์", caution: "ข้อสังเกตด้านคำศัพท์ขึ้นกับตัวอย่างบทถอดเสียงที่ทบทวน" },
        interaction: { label: "ปฏิสัมพันธ์", caution: "ทบทวนร่วมกับบทบาทของผู้พูดและบริบทของปฏิสัมพันธ์" },
        "speech-intelligibility": {
          label: "การพูด / ความชัดเจน",
          caution: "ข้อสังเกตจากบทถอดเสียงใช้แทนการประเมินการพูดโดยตรงไม่ได้",
        },
        "data-quality": { label: "คุณภาพข้อมูล", caution: "แก้ปัญหาคุณภาพข้อมูลที่สำคัญก่อนนำไปใช้ในรายงาน" },
      },
      hide: "ซ่อนหลักฐานและข้อจำกัด",
      show: "หลักฐานและข้อจำกัด",
      method: "วิธีคำนวณ",
      limitations: "ข้อจำกัด",
      caution: "ข้อควรระวังในการตีความทางคลินิก",
      emptyGroup: "เซสชันนี้ไม่มีค่าในกลุ่มนี้",
      footer: "ค่าเหล่านี้เป็นข้อสังเกตเชิงพรรณนาจากบทถอดเสียงที่ทบทวนแล้ว ไม่ใช่ผลการวินิจฉัย ให้พิจารณาร่วมกับบริบทของนักบำบัด",
    },
    evidence: {
      summary: "แนวทางการทบทวนและหลักฐาน",
      reviewPoints: (count) => `${count} จุดที่ควรทบทวน`,
      recommended: "จุดที่แนะนำให้ทบทวน",
      providerLine: (name, version, schema) => `${name} v${version} · schema ${schema}`,
      notComputed: "ไม่ได้คำนวณ",
      adult: "ผู้ใหญ่:",
      child: "เด็ก:",
      lineGone: "(บรรทัดนี้ไม่อยู่ในบทถอดเสียงแล้ว)",
      repeatsWhole: "พูดซ้ำคำพูดของผู้ใหญ่",
      repeatsPart: "พูดซ้ำบางส่วนของคำพูดของผู้ใหญ่",
      next: (step) => `ขั้นต่อไป: ${step}`,
      confirm: "ยืนยันหลังตรวจแล้ว",
      dismiss: "ไม่นับ — ไม่ใช่การพูดซ้ำหรือปัญหาสรรพนาม",
      confirmed: "นักบำบัดยืนยันแล้ว",
      dismissed: "นักบำบัดไม่นับ",
      notReviewed: "ยังไม่ได้ทบทวน",
      openTranscript: "เปิดบทถอดเสียง",
      profile: (code) => `โปรไฟล์ ${code}`,
      presentationGroup: (group) => `กลุ่มลักษณะ: ${group}`,
      referenceSupport: (participants, corpora) => `ข้อมูลอ้างอิง: ผู้เข้าร่วม ${participants} คน · ${corpora} คลังข้อมูล`,
      observed: (value, position) => `ค่าที่พบ ${value} · ${position}`,
      distribution: (q1, median, q3) => `การกระจายของค่าอ้างอิง Q1 ${q1} · มัธยฐาน ${median} · Q3 ${q3}`,
      reviewed: "ทบทวนแล้ว",
      recordDisagreement: "บันทึกความเห็นต่าง",
      disagreementNote: "บันทึกนี้เก็บความเห็นต่างทางคลินิก และคงผลลัพธ์เดิมของระบบไว้",
      disagreementLabel: (code) => `บันทึกความเห็นต่างสำหรับ ${code}`,
      saveDisagreement: "บันทึกความเห็นต่าง",
      cancel: "ยกเลิก",
      hideEvidence: "ซ่อนหลักฐานประกอบ",
      viewEvidence: "ดูหลักฐานประกอบ",
    },
    availability: {
      canContinue: "ทำขั้นตอนค่าทางภาษาและรายงานต่อได้",
      actionRequired: "ต้องดำเนินการในขั้นตอนก่อนจึงจะไปต่อได้",
      next: (step) => `ขั้นต่อไป: ${step}`,
    },
  },
});
