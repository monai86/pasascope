# ชุดข้อมูลประเมิน ASR ภาษาไทย

ชุดนี้ใช้วัดว่าร่าง transcript จาก Whisper ใกล้เคียงกับ transcript ที่คนถอดเองแค่ไหน
ผลที่ได้ใช้เป็นตัวเลขในบทผลการทดลองของ term paper

| โฟลเดอร์ | ใส่อะไร |
|---|---|
| `.local/evaluation/audio_samples/` | ไฟล์เสียง เช่น `clip01.wav` (รองรับ wav, mp3, m4a, mp4, webm, ogg, flac) |
| `data/evaluation/gold_transcripts/` | transcript ที่คนถอดและตรวจแล้ว ชื่อเดียวกับไฟล์เสียง เช่น `clip01.cha` |
| `.local/evaluation/hypothesis_transcripts/` | ร่างจาก ASR สคริปต์สร้างให้เอง ไม่ต้องแก้ด้วยมือ |

## การประเมินที่ไม่ต้องอัดเสียงเอง

โครงการนี้ไม่มีชุดข้อมูลเสียงเด็กไทย การประเมินจึงแยกเป็นส่วนที่ทำได้ด้วยข้อมูลที่มีอยู่
แต่ละส่วนตอบคำถามคนละข้อ และรันซ้ำได้ด้วยคำสั่งเดียว

| คำถาม | ข้อมูล | คำสั่ง | ผลลัพธ์ |
|---|---|---|---|
| ระบบคำนวณ feature จาก transcript ถูกไหม | transcript TalkBank 1,961 ไฟล์ เทียบกับ CLAN | `python scripts/evaluate_feature_agreement_clan.py` | `reports/metrics/feature_agreement_clan.md` |
| Whisper ถอดภาษาไทยได้แม่นแค่ไหน | FLEURS ภาษาไทย (ผู้ใหญ่อ่านประโยค, CC BY 4.0) ดาวน์โหลดอัตโนมัติ | `python scripts/evaluate_thai_asr_public.py --clips 30 --models small medium` | `reports/metrics/thai_asr_public.md` |
| ถอดบทสนทนาแบบในห้องบำบัดได้ไหม | บทสนทนาไทยสังเคราะห์ด้วยเสียง TTS ของ macOS | `python scripts/build_synthetic_thai_dialogues.py` แล้ว `python scripts/evaluate_thai_asr.py --text-only` | `reports/metrics/thai_asr_evaluation.md` |
| กฎตรวจ echolalia จับถูกไหม | คู่ประโยค 40 คู่ที่ติดป้ายไว้ใน `echolalia_labelled_pairs.csv` | `python scripts/evaluate_echolalia_cue.py` | `reports/metrics/echolalia_cue_check.md` |

สิ่งที่ชุดนี้ยังวัดไม่ได้คือความแม่นยำกับเสียงเด็กจริง และการแยกผู้พูดเด็ก/ผู้ใหญ่ในภาษาไทย
เพราะเสียงสังเคราะห์เป็นเสียงเดียวกันทุกบท ต้องเขียนเป็นข้อจำกัดในเล่ม
ส่วนด้านล่างคือวิธีเพิ่มข้อมูลของคุณเองเมื่อมีโอกาสอัดเสียง

## ข้อห้าม

ห้ามใส่เสียงเด็กจริง ชื่อจริง หรือข้อมูลที่ระบุตัวบุคคลได้ในโฟลเดอร์นี้
ให้ใช้เสียงจำลองที่ผู้ใหญ่เล่นบทนักบำบัดกับเด็กเท่านั้น
ไฟล์เสียงและร่างอยู่ใต้ `.local/` (โฟลเดอร์ที่ root ของ repo) ซึ่งไม่ถูก commit และตัวตรวจ repo จะไม่ยอมให้มีไฟล์เสียงที่อื่น

## วิธีอัดเสียงจำลอง

- อัด 5–10 คลิป คลิปละ 1–3 นาที ด้วยไมโครโฟนตัวเดียว ในห้องเงียบ
- ใช้สองคน คนหนึ่งเล่นเป็นนักบำบัด อีกคนเล่นเป็นเด็กโดยพูดเสียงสูงกว่าและประโยคสั้นกว่า
  (ตัวแยกผู้พูดอาศัยระดับเสียง ถ้าใช้คนเดียวพูดสองบท ผลการแยกผู้พูดจะใช้ไม่ได้)
- เว้นจังหวะระหว่างผลัดพูดประมาณครึ่งวินาที
- ให้บางคลิปมีการพูดตาม (echolalia) เพื่อทดสอบการตรวจจับ และบางคลิปไม่มีเลยเพื่อเป็นตัวเปรียบเทียบ
- จดไว้ว่าคลิปไหนอัดอย่างไร (ผู้พูด อุปกรณ์ ห้อง) เพื่อเขียนในหัวข้อวิธีการทดลอง

ตัวอย่างบทพูดที่มีการพูดตาม:

```
นักบำบัด: วันนี้เราจะเล่นอะไรกันดี
เด็ก:     เล่นอะไรกันดี
นักบำบัด: เล่นรถไหมครับ
เด็ก:     เล่นรถ
นักบำบัด: รถสีอะไรครับ
เด็ก:     สีแดง
```

## รูปแบบ gold transcript

ถอดตามที่พูดจริงในคลิป ไม่ใช่ตามบทที่เตรียมไว้ หนึ่งบรรทัดต่อหนึ่งประโยค
ใช้ `*INV:` สำหรับนักบำบัด และ `*CHI:` สำหรับเด็ก คั่นด้วย tab และจบด้วย ` .`
เว้นวรรคระหว่างคำหรือไม่ก็ได้ เพราะสคริปต์ตัดคำให้ทั้งสองฝั่งด้วยวิธีเดียวกัน

```
@UTF8
@Begin
@Languages:	tha
*INV:	วันนี้เราจะเล่นอะไรกันดี .
*CHI:	เล่นอะไรกันดี .
*INV:	เล่นรถไหมครับ .
*CHI:	เล่นรถ .
@End
```

## รันการประเมิน

```bash
python scripts/evaluate_thai_asr.py                 # ถอดเสียงแล้วให้คะแนน
python scripts/evaluate_thai_asr.py --score-only    # ให้คะแนนจากร่างที่บันทึกไว้ ไม่ถอดใหม่
python scripts/evaluate_thai_asr.py --model small   # เทียบขนาดโมเดล (ค่าเริ่มต้นคือ medium)
```

ผลลัพธ์อยู่ที่ `reports/metrics/thai_asr_evaluation.csv` และ `.md`

## อ่านค่าอย่างไร

| ค่า | ความหมาย |
|---|---|
| WER / CER all | อัตราคำผิด / ตัวอักษรผิดของทั้งบทสนทนา ยิ่งต่ำยิ่งดี |
| WER / CER child | เทียบเฉพาะข้อความที่ระบุว่าเป็นของเด็ก จึงรวมความผิดจากการแยกผู้พูดด้วย |
| MLU-w, TTR, Echolalia (gold/draft) | ค่า feature จาก gold เทียบกับร่าง แสดงว่าถ้าไม่แก้ร่าง ค่าจะคลาดไปเท่าไร |
| RTF | เวลาประมวลผลหารด้วยความยาวเสียง เช่น 1.5 คือคลิป 1 นาทีใช้เวลา 1.5 นาที |

ผลจากเสียงจำลองของผู้ใหญ่ไม่ได้บอกความแม่นยำกับเสียงเด็กจริง ให้ระบุข้อจำกัดนี้ในเล่มด้วย

## วัดเวลาที่ใช้แก้ร่าง

หลังจากอัปโหลดคลิปผ่าน Web app แก้ร่าง และกด attest แล้ว รัน:

```bash
python scripts/report_transcript_review_time.py
```

ได้เวลาตั้งแต่ร่างพร้อมจนถึง attest ของแต่ละคลิป ที่ `reports/metrics/transcript_review_time.csv`
ค่านี้เป็นเวลาตามนาฬิกา จึงรวมช่วงที่ผู้ตรวจหยุดพักด้วย ควรแก้ต่อเนื่องให้จบในครั้งเดียว
และจับเวลาถอดเองทั้งคลิปแยกไว้เพื่อใช้เปรียบเทียบ

## วัดการแยกเสียงเด็กกับผู้ใหญ่

ตัวชี้วัดทุกตัวคำนวณจากประโยคที่ติดป้าย `*CHI` ถ้าแยกผู้พูดผิด MLU และ NDW จะคลาดเท่ากับถอดเสียงผิด
`scripts/evaluate_speaker_attribution.py` ใช้ไฟล์ CHAT ที่มีเวลาทุกประโยค (time bullet) เป็นเฉลย
ส่งช่วงเวลาของแต่ละประโยคให้ตัวแยกผู้พูด แล้วเทียบป้ายเด็ก/ผู้ใหญ่ที่ได้กับเฉลย ไม่ได้รัน ASR
จึงวัดเฉพาะการแยกผู้พูด และคำนวณ MLU-w กับ NDW จากป้ายเฉลยเทียบกับป้ายที่ระบบให้ด้วย

### เสียงเด็กจริงจาก TalkBank (ภาษาอังกฤษ)

transcript ใน `data/curated/english_child_transcripts/` ของ EllisWeismer (เด็ก 2.5–5 ปีคุยกับผู้ตรวจ)
และ ENNI (เด็ก 4–9 ปี เล่านิทานจากภาพ กลุ่ม SLI และ TD) มีเวลาทุกประโยค แต่ไฟล์เสียงต้องล็อกอิน TalkBank (สมัครฟรี) ดาวน์โหลดเอง:

1. ล็อกอินที่ https://talkbank.org แล้วเปิด https://media.talkbank.org/childes/Clinical-Eng/EllisWeismer/
2. ดาวน์โหลดไฟล์เสียงที่ชื่อตรงกับ `@Media` ของ transcript สัก 10–20 ไฟล์ ใส่โฟลเดอร์เดียวกัน
3. รัน:

```bash
python scripts/evaluate_speaker_attribution.py \
    --cha-dir data/curated/english_child_transcripts/EllisWeismer \
    --audio-dir ~/Downloads/EllisWeismer-media --backend hybrid --max-minutes 10
```

ผลอยู่ที่ `reports/metrics/speaker_attribution_hybrid.{md,csv}`
`--backend` เลือกได้: `hybrid` (ค่าเริ่มต้นของโปรแกรม), `usc`, `embedding` (แบบเดิม), `pitch`
`--text none` วัดจากเสียงอย่างเดียว (ไม่ให้ระบบเห็นข้อความ)
ถ้า transcript หลายไฟล์ใช้ชื่อสื่อเดียวกัน (เด็กคนเดียวกันต่างอายุ) สคริปต์จะไม่จับคู่ ให้ใส่ `--cha-dir` ที่มีเฉพาะ transcript ของไฟล์เสียงที่โหลดมา
ผลกับเสียงเด็กจริง 16 ไฟล์อยู่ที่ `reports/metrics/speaker_attribution_real_children.md`
และ `scripts/tune_speaker_attribution.py` ใช้เทียบและปรับค่าแบบแยกชุดปรับกับชุดทดสอบ

### เสียงภาษาไทย

CHILDES มีคลัง CRSLP (เด็กไทย 1;8–2;0 ปี เล่นของเล่นกับพ่อแม่ วิดีโอ) ที่ media.talkbank.org/childes/EastAsian/Thai/CRSLP/
transcript ของ CRSLP เขียนเป็นภาษาไทยเว้นวรรคระหว่างคำและมีเวลาทุกประโยค
วาง transcript ไว้ที่ `chat/<โฟลเดอร์เด็ก>/` และวิดีโอที่ `<โฟลเดอร์เด็ก>/` ให้ชื่อโฟลเดอร์ตรงกัน
(CRSLP ใช้ชื่อไฟล์ซ้ำข้ามเด็ก สคริปต์จะจับคู่ไฟล์ในโฟลเดอร์ชื่อเดียวกันก่อน):

```bash
python scripts/evaluate_speaker_attribution.py --cha-dir .local/evaluation/crslp_media/chat \
    --audio-dir .local/evaluation/crslp_media --backend hybrid --text none --max-minutes 10 \
    --report-dir reports/metrics/crslp
```

หรืออัดคลิปเองที่รู้ว่าใครพูดช่วงไหน แล้วทำ CHAT ที่มีเวลาทุกประโยค (ส่งออกจากหน้าตรวจ transcript ของโปรแกรมหลังแก้ผู้พูดให้ถูก)
ใส่ไฟล์ `.cha` กับไฟล์เสียงชื่อเดียวกับ `@Media` แล้วรันคำสั่งเดียวกัน

### ช่วงอายุที่ใช้ได้

ป้ายผู้พูดเชื่อได้เฉพาะเด็กอายุ 30–83 เดือน ซึ่งเป็นช่วงที่ตรวจแล้ว (EllisWeismer, ENNI)
เด็กที่เล็กกว่าหรือโตกว่านี้ โปรแกรมจะติด ? ทุกประโยคให้นักบำบัดตรวจผู้พูดเอง
ผลอยู่ที่ `reports/metrics/speaker_attribution_thai_toddlers.md` และ `reports/metrics/speaker_attribution_real_children.md`

## จำลองโมเดลแยกเสียงประจำคลินิก

`scripts/evaluate_clinic_speaker_model.py` จำลองการที่โปรแกรมเรียนจาก session ที่นักบำบัดรับรองแล้ว
โดยใช้ป้ายผู้พูดจาก transcript เฉลยแทนการรับรอง: เรียนจาก N ไฟล์ของคลังเดียวกันแล้วทดสอบกับเด็กที่ไม่เคยเห็น,
เรียนจากคลังอื่นแล้วทดสอบ และรันการตรวจก่อนใช้แบบเดียวกับในโปรแกรม
feature ของแต่ละไฟล์เก็บไว้ที่ `.local/evaluation/speaker_features/` รอบต่อไปจึงเทรนอย่างเดียว

```bash
python scripts/evaluate_clinic_speaker_model.py \
    --corpus enni=.local/evaluation/enni_media \
    --corpus ellisweismer=.local/evaluation/ellisweismer_media \
    --corpus crslp=.local/evaluation/crslp_media
```

ผลอยู่ที่ `reports/metrics/clinic_speaker_model.{md,csv}`

## วัดทั้งสาย: เสียง → ร่าง → MLU/NDW ของเด็ก

`scripts/evaluate_end_to_end.py` รันไฟล์เสียงผ่านขั้นตอนเดียวกับโปรแกรม (Whisper, ตัดประโยคที่ช่วงเงียบ, แยกผู้พูด, ร่างแบบ CHAT)
แล้วคำนวณตัวชี้วัดของเด็กจากร่างที่ยังไม่แก้ เทียบกับ transcript เฉลย
นับเฉพาะช่วงเวลาตั้งแต่ก่อนประโยคแรกที่ถอดไว้ 2 วินาที ไปอีก `--minutes` นาที
ถ้าแบ่ง transcript ไว้ในโฟลเดอร์ย่อยเป็นกลุ่ม (เช่น `SLI/` กับ `TD/`) และแต่ละกลุ่มมีอย่างน้อย 3 ไฟล์
รายงานจะเทียบค่าเฉลี่ยและขนาดผล (Cohen's d) ระหว่างกลุ่ม ทั้งจากเฉลยและจากร่าง

```bash
python scripts/evaluate_end_to_end.py --cha-dir .local/evaluation/enni_media/chat \
    --audio-dir .local/evaluation/enni_media --minutes 10 --name enni
python scripts/evaluate_end_to_end.py --cha-dir .local/evaluation/crslp_media/chat \
    --audio-dir .local/evaluation/crslp_media --minutes 3 --limit 8 --strategy thai_specialized --name crslp
```

ผลอยู่ที่ `reports/metrics/end_to_end_<name>.{md,csv}` ส่วนร่างแต่ละไฟล์อยู่ที่ `.local/evaluation/end_to_end_drafts/<name>/`
`--report-only` เขียนรายงานใหม่จาก CSV เดิมโดยไม่ต้องรันเสียงซ้ำ

### อ่านค่าอย่างไร

| ค่า | ความหมาย |
|---|---|
| Utterance accuracy | สัดส่วนประโยคที่ติดป้ายเด็ก/ผู้ใหญ่ถูก |
| Child precision | ประโยคที่ระบบบอกว่าเป็นเด็ก เป็นเด็กจริงกี่ % ถ้าต่ำ คำของผู้ใหญ่จะปนเข้ามาในตัวชี้วัดของเด็ก |
| Child recall | ประโยคของเด็กจริง ระบบหาเจอกี่ % ถ้าต่ำ คำของเด็กจะหายไปจากตัวชี้วัด |
| MLU / NDW shift | ตัวชี้วัดคลาดไปเท่าไรเพราะการแยกผู้พูดอย่างเดียว |

เสียงสังเคราะห์ (`say` ของ macOS) ใช้ตรวจว่าเครื่องมือทำงานได้เท่านั้น ไม่ใช่หลักฐานความแม่นยำกับเสียงเด็ก
