import Link from "next/link";
import { ShieldCheck, Download, Star, Heart, ArrowRight, AlertCircle, CheckCircle2, FileText, ArrowLeft } from "lucide-react";

export default function DemoReport() {
  const tableData = [
    { name: "Turn Count", value: "12 รอบ", status: "บันทึกได้", color: "text-[color:var(--color-success-text)] bg-[color:var(--color-success-bg)] border-[color:var(--color-success-border)]" },
    { name: "Total Words", value: "28 คำ", status: "ข้อมูลเชิงพรรณนา", color: "text-[color:var(--color-warning-text)] bg-[color:var(--color-warning-bg)] border-[color:var(--color-attention-border)]" },
    { name: "MLU (Mean Length)", value: "2.3", status: "ข้อมูลเชิงพรรณนา", color: "text-[color:var(--color-warning-text)] bg-[color:var(--color-warning-bg)] border-[color:var(--color-attention-border)]" },
    { name: "TTR (Vocab Diversity)", value: "0.71", status: "ข้อมูลเชิงพรรณนา", color: "text-[color:var(--color-success-text)] bg-[color:var(--color-success-bg)] border-[color:var(--color-success-border)]" },
    { name: "Vocabulary Size", value: "20 คำ", status: "ข้อมูลเชิงพรรณนา", color: "text-[color:var(--color-warning-text)] bg-[color:var(--color-warning-bg)] border-[color:var(--color-attention-border)]" },
    { name: "Response Rate", value: "100%", status: "ตอบครบในตัวอย่าง", color: "text-[color:var(--color-success-text)] bg-[color:var(--color-success-bg)] border-[color:var(--color-success-border)]" },
  ];

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full bg-[color:var(--color-warning-bg)] px-3 py-1 text-xs font-semibold text-[color:var(--color-warning-text)] border border-[color:var(--color-attention-border)]">
              <FileText size={12} />
              DRAFT — รอการลงนามรับรองจากนักบำบัด
            </span>
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-ink">
            รายงานผลการบำบัดภาษาและพูด (Progress Report)
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            รายงานตัวอย่างสรุปข้อมูลการสื่อสารจากเซสชัน เพื่อให้นักบำบัดทบทวนก่อนสื่อสารกับผู้ปกครอง
          </p>
        </div>
        <div className="flex flex-wrap gap-2 shrink-0">
          <button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-line bg-white px-4 text-sm font-semibold text-ink transition hover:bg-surface-soft">
            <Download size={16} />
            ส่งออก PDF
          </button>
          <button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-brand px-4 text-sm font-semibold text-white transition hover:bg-brand-strong">
            <ShieldCheck size={16} />
            ลงนามรับรอง (Sign-off)
          </button>
        </div>
      </div>

      {/* Meta Grid */}
      <div className="grid gap-4 rounded-panel border border-line bg-surface p-5 md:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="text-xs text-ink-subtle font-medium">ผู้เข้าร่วมตัวอย่าง</p>
          <p className="text-sm font-semibold text-ink mt-0.5">น้องเอ (Ava)</p>
        </div>
        <div>
          <p className="text-xs text-ink-subtle font-medium">อายุในข้อมูลตัวอย่าง</p>
          <p className="text-sm font-semibold text-ink mt-0.5">5 ปี 2 เดือน</p>
        </div>
        <div>
          <p className="text-xs text-ink-subtle font-medium">วันที่บันทึกตัวอย่าง</p>
          <p className="text-sm font-semibold text-ink mt-0.5">5 กรกฎาคม 2569</p>
        </div>
        <div>
          <p className="text-xs text-ink-subtle font-medium">นักบำบัดตัวอย่าง</p>
          <p className="text-sm font-semibold text-ink mt-0.5">Dr. Somchai K.</p>
        </div>
      </div>

      {/* Report Sections */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {/* Assessment Summary */}
          <div className="rounded-panel border border-line bg-surface p-6 space-y-3">
            <h3 className="text-lg font-bold text-ink flex items-center gap-2">
              <FileText size={20} className="text-brand" />
              สรุปข้อมูลจากเซสชันตัวอย่าง (Sample Session Summary)
            </h3>
            <p className="text-sm text-ink-muted leading-relaxed">
              ผู้เข้ารับการประเมินมีปฏิสัมพันธ์ผ่านเซสชันภาษาพูดในรูปแบบการเล่น ตัวอย่างนี้บันทึกรอบปฏิสัมพันธ์ 12 รอบและการตอบสนองต่อคำถามทุกครั้ง โดยคำพูดส่วนใหญ่เป็นคำโดดหรือประโยคสั้นและมีความยาวเฉลี่ย 2.3 คำ ข้อมูลนี้เป็นคำอธิบายตัวอย่างเพื่อให้นักบำบัดทบทวนร่วมกับบริบทเท่านั้น ไม่ได้ใช้เปรียบเทียบตามช่วงวัยหรือเป็นข้อสรุปเชิงวินิจฉัย
            </p>
          </div>

          {/* Strengths & Areas to monitor */}
          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-panel border-l-4 border-brand bg-surface p-6 space-y-3">
              <h4 className="font-bold text-[color:var(--color-success-text)] flex items-center gap-1.5 text-sm">
                <Star size={16} className="fill-[color:var(--color-success-text)]" />
                รูปแบบที่สังเกตได้ (Observed Patterns)
              </h4>
              <ul className="space-y-2 text-xs text-ink-muted list-disc pl-4 leading-relaxed">
                <li>ตอบกลับคู่สนทนาได้รวดเร็ว ครบถ้วน (Response Rate 100%)</li>
                <li>พบคำไม่ซ้ำ 20 คำจากคำพูดทั้งหมด 28 คำในตัวอย่างที่บันทึกไว้</li>
                <li>แสดงอารมณ์ร่วมและการเล่นตามบทบาทกับตุ๊กตาได้ต่อเนื่อง</li>
              </ul>
            </div>

            <div className="rounded-panel border-l-4 border-[color:var(--color-warning-border)] bg-surface p-6 space-y-3">
              <h4 className="font-bold text-[color:var(--color-warning-text)] flex items-center gap-1.5 text-sm">
                <Heart size={16} className="fill-[color:var(--color-warning-text)]" />
                ประเด็นสำหรับนักบำบัดทบทวน (Review Prompts)
              </h4>
              <ul className="space-y-2 text-xs text-ink-muted list-disc pl-4 leading-relaxed">
                <li>ตัวอย่างมีความยาวคำพูดเฉลี่ย 2.3 คำ และหลายรอบประกอบด้วยคำพูด 2 คำ</li>
                <li>นักบำบัดอาจทบทวนคำกริยาและคำขยายที่พบ ก่อนเลือกกิจกรรมครั้งถัดไป</li>
              </ul>
            </div>
          </div>

          {/* Recommendations */}
          <div className="rounded-panel border-l-4 border-brand bg-surface p-6 space-y-3">
            <h3 className="text-sm font-bold text-brand-strong flex items-center gap-2">
              <ArrowRight size={16} />
              ตัวอย่างกิจกรรมสำหรับพิจารณา (Activities for Therapist Review)
            </h3>
            <ul className="space-y-2 text-xs text-ink-muted list-decimal pl-4 leading-relaxed">
              <li><strong>กิจกรรมกระตุ้นขยายคำ (Recasting):</strong> แนะนำให้ผู้ปกครองและนักบำบัดขยายความประโยคพูดของเด็กทันที เช่น เด็กพูด &quot;มิกกี้กินข้าว&quot; ให้ขยายเป็น &quot;ใช่ค่ะ มิกกี้กำลังกินข้าวผัดอร่อยมากเลย&quot;</li>
              <li><strong>การเล่าเรื่องผ่านหนังสือภาพ (Shared Book Reading):</strong> ชวนดูหนังสือภาพแล้วถามคำถามปลายเปิดเพื่อดึงการอธิบายประโยคยาว</li>
              <li><strong>ตัวอย่างภาษาครั้งถัดไป:</strong> หากเหมาะสม นักบำบัดอาจเก็บตัวอย่างอีกครั้งเพื่อดูการเปลี่ยนแปลงของข้อมูลเชิงพรรณนา</li>
            </ul>
          </div>
        </div>

        {/* Feature Table (Right rail style) */}
        <div className="rounded-panel border border-line bg-surface p-5 space-y-4 h-fit">
          <h3 className="font-semibold text-sm text-ink border-b border-line pb-2 flex items-center gap-1.5">
            <CheckCircle2 size={16} className="text-[color:var(--color-success-text)]" />
            สรุปผลตัวแปรทางภาษา (Linguistic Profile)
          </h3>
          <div className="overflow-hidden">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-line text-ink-subtle font-medium">
                  <th className="py-2">ตัวชี้วัด (Features)</th>
                  <th className="py-2 text-right">ค่า</th>
                  <th className="py-2 text-right">สถานะ</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line text-ink">
                {tableData.map((row) => (
                  <tr key={row.name}>
                    <td className="py-2.5 font-medium">{row.name}</td>
                    <td className="py-2.5 text-right font-semibold">{row.value}</td>
                    <td className="py-2.5 text-right">
                      <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-bold border ${row.color}`}>
                        {row.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="rounded-xl border border-line bg-surface-soft p-4 text-xs text-ink-muted text-center leading-normal">
        🛡️ <strong>Clinical Safety Gate:</strong> หน้านี้เป็นข้อมูลตัวอย่างจาก PasaScope Therapist Workspace สำหรับสนับสนุนการทบทวนโดยนักบำบัดเท่านั้น ไม่ใช่เครื่องมือวินิจฉัยและห้ามใช้เพื่อวินิจฉัย การลงนามไม่เปลี่ยนข้อจำกัดนี้
      </div>

      {/* Action Buttons Bottom */}
      <div className="flex items-center justify-between border-t border-line pt-6">
        <Link
          href="/demo/features"
          className="inline-flex min-h-11 items-center justify-center rounded-full border border-line bg-white px-5 text-sm font-semibold text-ink transition hover:bg-surface-soft"
        >
          ย้อนกลับ
        </Link>
        <Link
          href="/demo/parent"
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-brand px-6 text-sm font-semibold text-white transition hover:bg-brand-strong"
        >
          ถัดไป: หน้าสำหรับผู้ปกครอง (Parent Portal Mock)
          <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
}
