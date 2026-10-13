# ขึ้นเว็บ PasaScope แบบสาธารณะ (สมัครแล้วใช้ได้เลย)

เอกสารนี้พาตั้งค่าระบบจริงสี่ส่วน ใช้บริการแบบฟรีทั้งหมด

| ส่วน | บริการ | ทำหน้าที่ |
|---|---|---|
| ฐานข้อมูล, ล็อกอิน, ที่เก็บไฟล์เสียง | Supabase | เก็บเคส/บทถอดเสียง/รายงาน, สมัครด้วยอีเมลหรือ Google, สำรองไฟล์เสียง |
| API | Render (แผนฟรี 512 MB) | รัน `apps/api` จาก `deploy/render/Dockerfile` |
| ถอดเสียง | Groq (Whisper `large-v3`) | รับไฟล์เสียงจาก API แล้วส่งบทถอดเสียงกลับ |
| หน้าเว็บ | Vercel | รัน `apps/pasascope-app` |

PasaScope เป็นต้นแบบเพื่อการวิจัยและการศึกษา ไม่ใช่เครื่องมือวินิจฉัย และยังไม่ผ่านการตรวจสอบทางคลินิกกับเด็กไทย

> Hugging Face Space แบบ Docker ต้องใช้แผนเสียเงินแล้ว จึงไม่ใช่ทางฟรีอีกต่อไป ถ้าต้องการให้เสียงอยู่ในระบบของเราเองทั้งหมด ดูหัวข้อ [ย้ายไปถอดเสียงบนเซิร์ฟเวอร์ของเราเอง](#5-ย้ายไปถอดเสียงบนเซิร์ฟเวอร์ของเราเอง) ท้ายเอกสาร

## สิ่งที่ต้องรู้ก่อนเปิดให้คนทั่วไปใช้

- เว็บจะเก็บ**เสียงพูดของเด็ก** บทถอดเสียง และรายงานของผู้ใช้ทุกคน ผู้ดูแลระบบมีหน้าที่ตาม PDPA ควรมีหน้านโยบายความเป็นส่วนตัวและช่องทางขอลบข้อมูลก่อนประกาศเว็บ
- **เสียงที่อัปโหลดเพื่อถอดเสียงถูกส่งออกไปที่ Groq** ซึ่งเป็นบริษัทภายนอก หน้าเว็บแจ้งเรื่องนี้ที่ตัวอัดเสียงและที่ช่องยืนยันความยินยอม ผู้ดูแลระบบต้องอ่านเงื่อนไขการเก็บข้อมูลของ Groq และระบุในนโยบายความเป็นส่วนตัว
- ข้อมูลแยกตามผู้ใช้: API สร้างพื้นที่ทำงาน `personal_<user id>` จาก token ของแต่ละคน ผู้ใช้เปิดข้อมูลของคนอื่นไม่ได้
- ไม่มีขั้น "รับรองบทถอดเสียง" และ "ลงนามรายงาน" ระบบบันทึกการรับรองให้อัตโนมัติเมื่อผู้ใช้กดวิเคราะห์ และระบุในบันทึกว่าเป็นการรับรองอัตโนมัติ
- **ร่างบทถอดเสียงไม่แยกผู้พูด** ทุกบรรทัดขึ้นเป็น `UNK` ผู้ใช้ต้องเลือกผู้พูดของแต่ละบรรทัดเอง และต้องตรวจแก้ถ้อยคำเทียบกับเสียงทุกครั้ง
- ไฟล์เสียงที่ส่งถอดเสียงได้ต้องไม่เกิน 25 MB และโควตาฟรีของ Groq มีเพดานรายวัน เมื่อเต็มงานถอดเสียงจะล้มเหลวพร้อมข้อความให้ลองใหม่ภายหลัง
- เซิร์ฟเวอร์ฟรีของ Render **หลับเมื่อไม่มีคนใช้ราว 15 นาที** คำขอแรกหลังตื่นใช้เวลาราว 1 นาที
- API เก็บข้อมูลทั้งหมดไว้ในหน่วยความจำของโปรเซสเดียว (`WEB_CONCURRENCY=1`) เหมาะกับผู้ใช้จำนวนน้อย

## 1. Supabase

1. **Authentication → Sign In / Providers**
   - เปิด *Allow new users to sign up*
   - Email: เปิดใช้ ถ้าอยากให้สมัครแล้วเข้าได้ทันทีให้ปิด *Confirm email*
   - Google: เปิดใช้ แล้วใส่ Client ID / Secret จาก Google Cloud Console → Google Auth Platform → Clients (Authorized redirect URI คือ `https://<ref>.supabase.co/auth/v1/callback`) ระหว่างที่แอปใน Google ยังเป็นสถานะ Testing จะล็อกอินด้วย Google ได้เฉพาะอีเมลที่เพิ่มเป็น Test users การเผยแพร่ต้องมีลิงก์หน้าแรกและหน้านโยบายความเป็นส่วนตัว (`https://<project>.vercel.app/privacy`) ในหน้า Branding ก่อน
2. **Authentication → URL Configuration**
   - *Site URL* = โดเมนของเว็บ เช่น `https://<project>.vercel.app`
   - *Redirect URLs* เพิ่ม `https://<project>.vercel.app/today` และ `https://<project>.vercel.app/login`
3. **Authentication → Hooks**: ปิด *Custom Access Token* hook เดิม (`pasascope_access_token_hook`) โหมดสาธารณะไม่ใช้ claim ขององค์กร
4. **Storage**: สร้าง bucket ชื่อ `audio-recordings` แบบ **private**
5. **Project Settings** จดค่าเหล่านี้ไว้ใช้ในขั้นถัดไป
   - Project URL (`https://<ref>.supabase.co`)
   - `anon` / publishable key (ใช้กับหน้าเว็บ)
   - `service_role` / secret key (ใช้กับ API เท่านั้น **ห้ามใส่ในหน้าเว็บ**)
   - Database → Connection string แบบ *Session pooler* แล้วเปลี่ยนขึ้นต้นเป็น `postgresql+psycopg://`

> ถ้าโปรเจกต์ Supabase เดิมเคยใช้กับรอบนำร่อง ตารางเดิมมีนโยบาย RLS ที่ผูกกับองค์กร แนะนำให้ใช้โปรเจกต์ใหม่หรือฐานข้อมูลว่างสำหรับเว็บสาธารณะ

## 2. Groq (ถอดเสียง)

1. สมัครที่ console.groq.com
2. เมนู **API Keys → Create API Key** ตั้งชื่อ เช่น `pasascope` แล้วคัดลอกคีย์ (ขึ้นต้นด้วย `gsk_`) เก็บไว้ใช้ในขั้นถัดไป คีย์แสดงครั้งเดียว

## 3. Render (API)

ไฟล์ [`render.yaml`](../render.yaml) กำหนดค่าทั้งหมดไว้แล้ว เหลือค่าลับ 4 ตัวที่ต้องกรอกเอง

1. เข้า dashboard.render.com → **New → Blueprint**
2. เชื่อม GitHub แล้วเลือก repository นี้ และเลือก branch ที่จะ deploy
3. Render จะอ่าน `render.yaml` และเสนอสร้าง service ชื่อ `pasascope-public-api` กรอก 4 ค่านี้

   | ชื่อ | ค่า |
   |---|---|
   | `PASASCOPE_CORS_ALLOWED_ORIGINS` | โดเมนของเว็บ เช่น `https://<project>.vercel.app` ไม่มี `/` ท้าย |
   | `PASASCOPE_DATABASE_URL` | connection string จากขั้น 1.5 |
   | `PASASCOPE_SUPABASE_STORAGE_SERVICE_ROLE_KEY` | service role key |
   | `PASASCOPE_ASR_HOSTED_API_KEY` | คีย์ Groq จากขั้น 2 |

4. กด **Apply** แล้วรอ build ราว 5 นาที
5. ตรวจว่า API ขึ้นแล้ว: เปิด `https://<service>.onrender.com/health` ต้องได้ `ok` และ `https://<service>.onrender.com/api/v1/settings` ต้องมี `"public_signup": true`, `"review_gates": "open"` และ `"transcription_provider": "hosted_whisper"`

ค่า URL ของ Supabase ใน `render.yaml` ชี้โปรเจกต์ที่ใช้กับเว็บสาธารณะ ถ้าเปลี่ยนโปรเจกต์ต้องแก้ 3 บรรทัดในไฟล์นั้น (JWKS URL, issuer, storage URL)

ไฟล์เสียงเขียนลงดิสก์ของ Render ก่อน แล้วสำรองขึ้น bucket ทันที เมื่อ service รีสตาร์ตและดิสก์ถูกล้าง API จะดึงไฟล์กลับจาก bucket เองตอนมีคนเปิดฟังหรือสั่งถอดเสียง

## 4. Vercel (หน้าเว็บ)

1. Project Settings → **Root Directory** = `apps/pasascope-app`, Node 22
2. **Environment Variables**
   | ชื่อ | ค่า |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://<service>.onrender.com/api/v1` |
   | `NEXT_PUBLIC_SUPABASE_URL` | `https://<ref>.supabase.co` |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | anon / publishable key |
   | `NEXT_PUBLIC_SITE_URL` | `https://<project>.vercel.app` |
   | `NEXT_PUBLIC_CONTACT_EMAIL` | (ไม่บังคับ) อีเมลสำหรับคำถามและคำขอลบข้อมูล แสดงในหน้า `/privacy` |
3. เลือก branch ที่จะ deploy เป็น production แล้วกด Redeploy

## ตรวจหลังขึ้นจริง

1. เปิดเว็บ → สมัครด้วยอีเมลใหม่ → ต้องเข้าหน้า **วันนี้** ได้ทันที
2. ล็อกอินด้วย Google ได้
3. สร้างเคส → ติ๊กยืนยันความยินยอม → เริ่มเซสชัน → อัดเสียง 30 วินาที → อัปโหลดเพื่อถอดเสียง → ได้ร่างบทถอดเสียง → เลือกผู้พูดของแต่ละบรรทัด
4. กด **วิเคราะห์บทถอดเสียงนี้** → เห็นค่าทางภาษา → สร้างร่างรายงาน → ส่งออก Markdown/HTML และพิมพ์ได้
5. สมัครบัญชีที่สอง → ต้อง**ไม่เห็น**เคสของบัญชีแรก
6. ที่หน้า service ของ Render กด *Manual Deploy → Restart service* → กลับมาเปิดเคสเดิม → เคส บทถอดเสียง และไฟล์เสียงยังอยู่

## ถ้ามีปัญหา

| อาการ | ตรวจที่ |
|---|---|
| ล็อกอินแล้วเด้งกลับหน้า login | `/api/v1/settings` ของ API มี `public_signup: true` หรือไม่; ค่า JWKS URL / issuer ตรงกับโปรเจกต์ Supabase หรือไม่ |
| หน้าเว็บขึ้น "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้" | API หลับอยู่ (รอราว 1 นาที); `PASASCOPE_CORS_ALLOWED_ORIGINS` ตรงกับโดเมนเว็บแบบไม่มี `/` ท้าย |
| อัปโหลดเสียงแล้วขึ้น "The recording could not be stored" | bucket ชื่อถูกและเป็นของโปรเจกต์เดียวกับ `PASASCOPE_SUPABASE_STORAGE_URL`; service role key ถูก |
| งานถอดเสียงล้มเหลว | ข้อความ "usage limit" = โควตา Groq เต็ม; "status 401" = คีย์ Groq ผิด; "larger than 25 MB" = ไฟล์ใหญ่เกิน |
| ข้อมูลหายหลังรีสตาร์ต | `PASASCOPE_REPOSITORY_MODE=sql` และ `PASASCOPE_DATABASE_URL` ชี้ฐานข้อมูล Supabase จริง |

## 5. ย้ายไปถอดเสียงบนเซิร์ฟเวอร์ของเราเอง

ใช้เมื่อไม่ต้องการส่งเสียงออกไปบริการภายนอก ต้องมีเครื่องที่ RAM อย่างน้อย 4 GB เช่น Hugging Face Space แบบ Docker (ต้องใช้แผน PRO) ข้อมูลใน Supabase อยู่ที่เดิม ไม่ต้องย้าย

สิ่งที่เปลี่ยนมีสามอย่าง: ที่รัน API, ค่าตั้งค่าการถอดเสียง (ปิด `PASASCOPE_ASR_HOSTED_ENABLED` แล้วเปิด `PASASCOPE_ASR_LOCAL_WHISPER_ENABLED`) และ `NEXT_PUBLIC_API_BASE_URL` ของหน้าเว็บ Whisper บนเครื่องแยกผู้พูดเด็ก/ผู้ใหญ่ให้ แต่ขนาด `small` บน CPU ใช้เวลาใกล้เคียงความยาวเสียงและภาษาไทยแม่นน้อยกว่า `large-v3`


1. สร้าง Space ใหม่ที่ huggingface.co: SDK = **Docker**, Hardware = **CPU basic (free)**, เปิดเป็น Public
2. ที่ **Settings → Variables and secrets** ใส่ค่าต่อไปนี้

   **Secrets**
   | ชื่อ | ค่า |
   |---|---|
   | `PASASCOPE_DATABASE_URL` | connection string จากขั้น 1.5 |
   | `PASASCOPE_SUPABASE_STORAGE_SERVICE_ROLE_KEY` | service role key |

   **Variables**
   | ชื่อ | ค่า |
   |---|---|
   | `PASASCOPE_MOCK_MODE` | `true` (ให้ใช้คิวงานในโปรเซสเดียวและสร้างตารางอัตโนมัติ) |
   | `PASASCOPE_AUTH_MODE` | `supabase` |
   | `PASASCOPE_SUPABASE_JWT_VERIFICATION_MODE` | `jwks_url` |
   | `PASASCOPE_SUPABASE_JWT_JWKS_URL` | `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json` |
   | `PASASCOPE_SUPABASE_JWT_ISSUER` | `https://<ref>.supabase.co/auth/v1` |
   | `PASASCOPE_SUPABASE_JWT_AUDIENCE` | `authenticated` |
   | `PASASCOPE_REPOSITORY_MODE` | `sql` |
   | `PASASCOPE_STORAGE_MODE` | `local_private` |
   | `PASASCOPE_AUDIO_BACKUP_MODE` | `supabase` |
   | `PASASCOPE_SUPABASE_STORAGE_URL` | `https://<ref>.supabase.co` |
   | `PASASCOPE_SUPABASE_STORAGE_BUCKET` | `audio-recordings` |
   | `PASASCOPE_ASR_LOCAL_WHISPER_ENABLED` | `true` |
   | `PASASCOPE_ASR_WHISPER_MODEL_SIZE` | `small` |
   | `PASASCOPE_CORS_ALLOWED_ORIGINS` | `https://<project>.vercel.app` |

3. ส่งโค้ดขึ้น Space จากเครื่องนี้
   ```bash
   hf auth login                                   # ครั้งแรกครั้งเดียว
   bash scripts/build_hf_space_bundle.sh           # สร้างชุดไฟล์ที่ .local/hf-space-bundle (ราว 4 MB)
   cd .local/hf-space-bundle
   git init -b main && git add -A && git commit -m "Deploy PasaScope API"
   git remote add space https://huggingface.co/spaces/<user>/<space>
   git push --force space main
   ```
   การ build ครั้งแรกใช้เวลาราว 15–20 นาที (ติดตั้ง PyTorch และ Whisper)
4. ตั้ง `NEXT_PUBLIC_API_BASE_URL` ของ Vercel เป็น `https://<user>-<space>.hf.space/api/v1` แล้ว Redeploy และปิด service เดิมบน Render
5. ตรวจว่า API ขึ้นแล้ว: เปิด `https://<user>-<space>.hf.space/health` ต้องได้ `ok` และ `https://<user>-<space>.hf.space/api/v1/settings` ต้องมี `"public_signup": true` และ `"review_gates": "open"`

ไฟล์เสียงเขียนลงดิสก์ของ Space ก่อน แล้วสำรองขึ้น bucket ทันที เมื่อ Space รีสตาร์ตและดิสก์ถูกล้าง API จะดึงไฟล์กลับจาก bucket เองตอนมีคนเปิดฟังหรือสั่งถอดเสียง
