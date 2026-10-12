import { defineMessages } from "@/i18n/messages";

/** Bar that assigns one speaker to every transcript line still labelled unknown. */
type SpeakerBulkCopy = {
  unassigned: (count: number) => string;
  setAllTo: string;
  child: string;
  therapist: string;
  hint: string;
};

export const speakerBulkMessages = defineMessages<SpeakerBulkCopy>({
  en: {
    unassigned: (count) => `${count} ${count === 1 ? "line has" : "lines have"} no speaker.`,
    setAllTo: "Set them all to",
    child: "Child (CHI)",
    therapist: "Therapist (THER)",
    hint: "Then change the lines spoken by the other person one by one.",
  },
  th: {
    unassigned: (count) => `มี ${count} บรรทัดที่ยังไม่ระบุผู้พูด`,
    setAllTo: "ตั้งทั้งหมดเป็น",
    child: "เด็ก (CHI)",
    therapist: "นักบำบัด (THER)",
    hint: "จากนั้นแก้บรรทัดที่อีกคนพูดทีละบรรทัด",
  },
});
