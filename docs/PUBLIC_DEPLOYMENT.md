# ขึ้นเว็บ PasaScope แบบสาธารณะ (สมัครแล้วใช้ได้เลย)

เอกสารนี้พาตั้งค่าระบบจริงสามส่วน ใช้บริการแบบฟรีทั้งหมด

| ส่วน | บริการ | ทำหน้าที่ |
|---|---|---|
| ฐานข้อมูล, ล็อกอิน, ที่เก็บไฟล์เสียง | Supabase | เก็บเคส/บทถอดเสียง/รายงาน, สมัครด้วยอีเมลหรือ Google, สำรองไฟล์เสียง |
| API และการถอดเสียง | Hugging Face Space (Docker) | รัน `apps/api` และ Whisper บนเครื่อง 2 vCPU / 16 GB |
| หน้าเว็บ | Vercel | รัน `apps/pasascope-app` |

PasaScope เป็นต้นแบบเพื่อการวิจัยและการศึกษา ไม่ใช่เครื่องมือวินิจฉัย และยังไม่ผ่านการตรวจสอบทางคลินิกกับเด็กไทย

## สิ่งที่ต้องรู้ก่อนเปิดให้คนทั่วไปใช้

- เว็บจะเก็บ**เสียงพูดของเด็ก** บทถอดเสียง และรายงานของผู้ใช้ทุกคน ผู้ดูแลระบบมีหน้าที่ตาม PDPA ควรมีหน้านโยบายความเป็นส่วนตัวและช่องทางขอลบข้อมูลก่อนประกาศเว็บ
- ข้อมูลแยกตามผู้ใช้: API สร้างพื้นที่ทำงาน `personal_<user id>` จาก token ของแต่ละคน ผู้ใช้เปิดข้อมูลของคนอื่นไม่ได้
- ไม่มีขั้น "รับรองบทถอดเสียง" และ "ลงนามรายงาน" ระบบบันทึกการรับรองให้อัตโนมัติเมื่อผู้ใช้กดวิเคราะห์ และระบุในบันทึกว่าเป็นการรับรองอัตโนมัติ
- Space แบบฟรี**หลับเมื่อไม่มีคนใช้** คำขอแรกหลังตื่นใช้เวลาราว 1–2 นาที
- Whisper ขนาด `small` บน CPU ใช้เวลาใกล้เคียงความยาวของเสียง และภาษาไทยแม่นปานกลาง ผู้ใช้ต้องแก้บทถอดเสียงเอง
- API เก็บข้อมูลทั้งหมดไว้ในหน่วยความจำของโปรเซสเดียว (`WEB_CONCURRENCY=1`) เหมาะกับผู้ใช้จำนวนน้อย

## 1. Supabase

1. **Authentication → Sign In / Providers**
   - เปิด *Allow new users to sign up*
   - Email: เปิดใช้ ถ้าอยากให้สมัครแล้วเข้าได้ทันทีให้ปิด *Confirm email*
   - Google: เปิดใช้ แล้วใส่ Client ID / Secret จาก Google Cloud Console (Authorized redirect URI คือค่าที่หน้า Supabase แสดง)
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

## 2. Hugging Face Space (API + ถอดเสียง)

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
   | `PASASCOPE_PUBLIC_SIGNUP` | `true` |
   | `PASASCOPE_REVIEW_GATES` | `open` |
   | `PASASCOPE_SUPABASE_REQUIRE_MFA` | `false` |
   | `PASASCOPE_SUPABASE_REQUIRE_INVITATION` | `false` |
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
4. ตรวจว่า API ขึ้นแล้ว: เปิด `https://<user>-<space>.hf.space/health` ต้องได้ `ok` และ `https://<user>-<space>.hf.space/api/v1/settings` ต้องมี `"public_signup": true` และ `"review_gates": "open"`

ไฟล์เสียงเขียนลงดิสก์ของ Space ก่อน แล้วสำรองขึ้น bucket ทันที เมื่อ Space รีสตาร์ตและดิสก์ถูกล้าง API จะดึงไฟล์กลับจาก bucket เองตอนมีคนเปิดฟังหรือสั่งถอดเสียง

## 3. Vercel (หน้าเว็บ)

1. Project Settings → **Root Directory** = `apps/pasascope-app`, Node 22
2. **Environment Variables**
   | ชื่อ | ค่า |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://<user>-<space>.hf.space/api/v1` |
   | `NEXT_PUBLIC_SUPABASE_URL` | `https://<ref>.supabase.co` |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | anon / publishable key |
   | `NEXT_PUBLIC_SITE_URL` | `https://<project>.vercel.app` |
   | `NEXT_PUBLIC_DEMO_MODE` | `false` |
3. เลือก branch ที่จะ deploy เป็น production แล้วกด Redeploy

## 4. ตรวจหลังขึ้นจริง

1. เปิดเว็บ → สมัครด้วยอีเมลใหม่ → ต้องเข้าหน้า **วันนี้** ได้ทันที
2. ล็อกอินด้วย Google ได้
3. สร้างเคส → ติ๊กยืนยันความยินยอม → เริ่มเซสชัน → อัดเสียง 30 วินาที → อัปโหลดเพื่อถอดเสียง → ได้ร่างบทถอดเสียง
4. กด **วิเคราะห์บทถอดเสียงนี้** → เห็นค่าทางภาษา → สร้างร่างรายงาน → ส่งออก Markdown/HTML และพิมพ์ได้
5. สมัครบัญชีที่สอง → ต้อง**ไม่เห็น**เคสของบัญชีแรก
6. ที่หน้า Space กด *Restart* → กลับมาเปิดเคสเดิม → เคส บทถอดเสียง และไฟล์เสียงยังอยู่

## ถ้ามีปัญหา

| อาการ | ตรวจที่ |
|---|---|
| ล็อกอินแล้วเด้งกลับหน้า login | `/api/v1/settings` ของ API มี `public_signup: true` หรือไม่; ค่า JWKS URL / issuer ตรงกับโปรเจกต์ Supabase หรือไม่ |
| หน้าเว็บขึ้น "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้" | Space หลับอยู่ (รอ 1–2 นาที); `PASASCOPE_CORS_ALLOWED_ORIGINS` ตรงกับโดเมนเว็บแบบไม่มี `/` ท้าย |
| อัปโหลดเสียงแล้วขึ้น "The recording could not be stored" | bucket ชื่อถูกและเป็นของโปรเจกต์เดียวกับ `PASASCOPE_SUPABASE_STORAGE_URL`; service role key ถูก |
| งานถอดเสียงค้างนาน | ดู Logs ของ Space ครั้งแรกต้องดาวน์โหลดโมเดล Whisper (ราว 500 MB) |
| ข้อมูลหายหลังรีสตาร์ต | `PASASCOPE_REPOSITORY_MODE=sql` และ `PASASCOPE_DATABASE_URL` ชี้ฐานข้อมูล Supabase จริง |
