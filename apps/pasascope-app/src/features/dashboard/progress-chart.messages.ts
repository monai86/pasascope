import { defineMessages } from "@/i18n/messages";

/** Language-progress chart strings; separate so Case detail does not load the dashboard catalog. */
export const progressChartMessages = defineMessages({
  en: {
    lineChart: (count: number) => `Line chart of ${count} value${count === 1 ? "" : "s"} across sessions`,
    openSession: (date: string) => `Open session ${date}`,
    empty: "No language-progress data yet. Extract features from a session to start tracking MLU, NDW, and TTR across sessions.",
    feature: "Feature",
    case: "Case",
    caseValue: "Case:",
    noData: (feature: string, caseLabel: string) =>
      `No ${feature.toLowerCase()} data for ${caseLabel} yet. Extract features from a language-sample session to see it here.`,
    oneSession: (feature: string) =>
      `One session with ${feature.toLowerCase()} data so far — add more sessions to see the trend line.`,
    unit: (unit: string, count: number) => `Unit: ${unit} · across ${count} session${count === 1 ? "" : "s"}`,
    reference: (ageBand: string, task: string, median: string, q1: string, q3: string) =>
      `Reference band (typical development, ${ageBand} months, ${task}): median ${median} · IQR ${q1}–${q3}`,
    tableCaption: (feature: string, caseLabel: string) => `${feature} values by session for ${caseLabel}`,
    sessionDate: "Session date",
  },
  th: {
    lineChart: (count: number) => `กราฟเส้นแสดง ${count} ค่าในแต่ละเซสชัน`,
    openSession: (date: string) => `เปิดเซสชันวันที่ ${date}`,
    empty: "ยังไม่มีข้อมูลความก้าวหน้าทางภาษา สกัดค่าทางภาษาจากเซสชันเพื่อเริ่มติดตาม MLU, NDW และ TTR ในแต่ละเซสชัน",
    feature: "ค่าที่ดู",
    case: "เคส",
    caseValue: "เคส:",
    noData: (feature: string, caseLabel: string) =>
      `ยังไม่มีข้อมูล ${feature} ของ ${caseLabel} สกัดค่าทางภาษาจากเซสชันตัวอย่างภาษาเพื่อดูที่นี่`,
    oneSession: (feature: string) => `ตอนนี้มีข้อมูล ${feature} เพียงหนึ่งเซสชัน เพิ่มเซสชันเพื่อดูเส้นแนวโน้ม`,
    unit: (unit: string, count: number) => `หน่วย: ${unit} · จาก ${count} เซสชัน`,
    reference: (ageBand: string, task: string, median: string, q1: string, q3: string) =>
      `ช่วงอ้างอิง (พัฒนาการทั่วไป, อายุ ${ageBand} เดือน, ${task}): มัธยฐาน ${median} · IQR ${q1}–${q3}`,
    tableCaption: (feature: string, caseLabel: string) => `ค่า ${feature} รายเซสชันของ ${caseLabel}`,
    sessionDate: "วันที่ของเซสชัน",
  },
});
