import { defineMessages } from "@/i18n/messages";
import type { AuthProblem } from "@/lib/supabase-auth-error";

type SupabaseLoginCopy = {
  title: string;
  subtitle: string;
  /** Wording for a deployment anyone can sign up to, where there is no clinic or organization. */
  open: {
    title: string;
    subtitle: string;
    signIn: string;
    createAccount: string;
    status: { signInAccepted: string; signUpConfirmEmail: string; recoverySent: string };
  };
  optional: string;
  passwordHint: (minimum: number) => string;
  passwordTooShort: (minimum: number) => string;
  /** The acknowledgement beside the tick box, with the privacy page's link in the middle. */
  acknowledge: { before: string; link: string; after: string; required: string };
  problems: Record<Exclude<AuthProblem, "other" | "weakPassword">, string>;
  emailHint: string;
  roles: { slp: string; admin: string; parent: string };
  modes: { signIn: string; signUp: string; invitationOnly: string };
  formLabel: string;
  displayName: string;
  displayNamePlaceholder: string;
  email: string;
  password: string;
  sendingRecovery: string;
  sendRecovery: string;
  hidePassword: string;
  showPassword: string;
  signingIn: string;
  signIn: string;
  signInLabel: string;
  configMissing: string;
  configInvalid: string;
  createAccountLabel: string;
  creatingAccount: string;
  createAccount: string;
  orContinueWith: string;
  connectingGoogle: string;
  continueWithGoogle: string;
  policyToggle: string;
  publicNote: { stored: string; boundary: string; privacy: string };
  policy: {
    invitationTitle: string;
    invitationOn: string;
    invitationOff: string;
    mfaTitle: string;
    mfaBefore: string;
    mfaMiddle: string;
    mfaAfter: string;
    organizationTitle: string;
    organizationBody: string;
    recoveryTitle: string;
    recoveryBody: string;
    runtimeBody: string;
    browserConfig: (status: string) => string;
  };
  status: {
    signUpSignedIn: string;
    signUpConfirmEmail: string;
    signInAccepted: string;
    recoverySent: string;
  };
  errors: {
    googleUnsupported: string;
    googleNotEnabled: string;
    googleFailed: string;
    configMissing: string;
    signUpUnsupported: string;
    signUpFailed: string;
    signInFailed: string;
    enterEmailFirst: string;
    recoveryFailed: string;
  };
};

export const supabaseLoginMessages = defineMessages<SupabaseLoginCopy>({
  en: {
    title: "Sign in to the clinic workspace",
    subtitle: "Sign in to open cases, session transcripts and reports.",
    open: {
      title: "Sign in to PasaScope",
      subtitle: "Open your cases, transcripts and reports, or create an account to begin.",
      signIn: "Sign in",
      createAccount: "Create account",
      status: {
        signInAccepted: "Signed in. Opening your workspace…",
        signUpConfirmEmail: "Check your inbox: open the message we sent to confirm your email, then sign in.",
        recoverySent: "If this email has an account, a recovery message is on its way.",
      },
    },
    optional: "optional",
    passwordHint: (minimum) => `At least ${minimum} characters. A phrase of several words works well; symbols and capitals are not required.`,
    passwordTooShort: (minimum) => `Use at least ${minimum} characters.`,
    acknowledge: {
      before: "I have read ",
      link: "how PasaScope stores and uses data",
      after: ".",
      required: "Tick the box to confirm you have read it.",
    },
    problems: {
      exists: "An account could not be created with this email. If it is yours, sign in or send a recovery email.",
      invalidCredentials: "The email or password is not right.",
      emailNotConfirmed: "Confirm your email first: open the message we sent and follow its link.",
      tooMany: "Too many attempts. Wait a few minutes and try again.",
      invalidEmail: "That email address is not valid.",
      signUpClosed: "New accounts are not open right now.",
      offline: "The sign-in service could not be reached. Check your connection and try again.",
    },
    emailHint: "Clinic email",
    roles: { slp: "Clinician / SLP", admin: "Clinic Admin", parent: "Parent" },
    modes: { signIn: "Sign in", signUp: "Create account", invitationOnly: "Invitation-only" },
    formLabel: "Supabase login form",
    displayName: "Display name",
    displayNamePlaceholder: "Your name",
    email: "Email",
    password: "Password",
    sendingRecovery: "Sending recovery email...",
    sendRecovery: "Send recovery email",
    hidePassword: "Hide password",
    showPassword: "Show password",
    signingIn: "Signing in...",
    signIn: "Sign in to the clinic workspace",
    signInLabel: "Sign in with Supabase",
    configMissing: "Supabase browser config missing",
    configInvalid: "Supabase browser config invalid",
    createAccountLabel: "Create Account",
    creatingAccount: "Creating account...",
    createAccount: "Create clinic account",
    orContinueWith: "Or continue with",
    connectingGoogle: "Connecting Google...",
    continueWithGoogle: "Continue with Google",
    policyToggle: "Clinical Security & Access Protocol Details",
    publicNote: {
      stored: "Your account keeps the cases, recordings, transcripts and reports you create. Other users cannot open them. Withdrawing a case's consent removes its recordings.",
      boundary: "PasaScope is a research and education prototype. It describes a language sample; it does not diagnose, and it has no Thai clinical validation.",
      privacy: "Privacy: what is stored and where it goes",
    },
    policy: {
      invitationTitle: "Invitation-only access",
      invitationOn: "Public signup is off. Only users with an accepted invitation can continue to account access.",
      invitationOff: "Runtime settings are not currently enforcing invitation-only onboarding.",
      mfaTitle: "MFA and app access",
      mfaBefore: "After invitation acceptance, TOTP MFA enrollment is mandatory.",
      mfaMiddle: "can reach MFA screens only, and",
      mfaAfter: "is required before any clinical or admin workflow access.",
      organizationTitle: "Organization session selection",
      organizationBody:
        "If multiple memberships are active, the user must explicitly choose one organization before workspace access. The last active organization is a hint only when the choice is ambiguous.",
      recoveryTitle: "Recovery and current runtime status",
      recoveryBody:
        "Password recovery uses the Supabase-managed reset path and still returns through membership and MFA gates before app access.",
      runtimeBody:
        "Browser sign-in now depends on the configured Supabase project and claim contract. Workspace access still fails closed until invitation, membership, MFA, and active organization requirements are satisfied.",
      browserConfig: (status) => `Browser config: ${status}`,
    },
    status: {
      signUpSignedIn: "Account created. Signing you in...",
      signUpConfirmEmail: "Account created. If email confirmation is required, open the message in your inbox to confirm, then sign in.",
      signInAccepted: "Sign-in accepted. Routing through organization and MFA access gates.",
      recoverySent: "Recovery email sent. App access still requires accepted membership and AAL2 after reset.",
    },
    errors: {
      googleUnsupported: "Google OAuth is not supported in this client configuration.",
      googleNotEnabled:
        "The Google provider is not enabled in the Supabase dashboard (Authentication > Providers > Google, with a client ID and secret).",
      googleFailed: "Google sign-in failed.",
      configMissing: "Supabase browser configuration is missing for this runtime.",
      signUpUnsupported: "Sign-up is not supported in this client configuration.",
      signUpFailed: "Sign-up failed.",
      signInFailed: "Sign-in failed.",
      enterEmailFirst: "Enter the invitation email address first.",
      recoveryFailed: "Recovery request failed.",
    },
  },
  th: {
    title: "ลงชื่อเข้าใช้พื้นที่ทำงานของคลินิก",
    subtitle: "ลงชื่อเข้าใช้เพื่อเปิดเคส บทถอดเสียงของเซสชัน และรายงาน",
    open: {
      title: "ลงชื่อเข้าใช้ PasaScope",
      subtitle: "เปิดเคส บทถอดเสียง และรายงานของคุณ หรือสร้างบัญชีเพื่อเริ่มใช้งาน",
      signIn: "ลงชื่อเข้าใช้",
      createAccount: "สร้างบัญชี",
      status: {
        signInAccepted: "ลงชื่อเข้าใช้แล้ว กำลังเปิดพื้นที่ทำงาน…",
        signUpConfirmEmail: "เปิดกล่องอีเมล แล้วกดลิงก์ในข้อความที่เราส่งไปเพื่อยืนยันอีเมล จากนั้นลงชื่อเข้าใช้",
        recoverySent: "ถ้าอีเมลนี้มีบัญชีอยู่ เราได้ส่งข้อความกู้คืนรหัสผ่านไปแล้ว",
      },
    },
    optional: "ไม่บังคับ",
    passwordHint: (minimum) => `อย่างน้อย ${minimum} ตัวอักษร ใช้วลีหลายคำได้ ไม่บังคับสัญลักษณ์หรือตัวพิมพ์ใหญ่`,
    passwordTooShort: (minimum) => `ใช้อย่างน้อย ${minimum} ตัวอักษร`,
    acknowledge: {
      before: "ฉันอ่าน",
      link: "วิธีที่ PasaScope เก็บและใช้ข้อมูล",
      after: "แล้ว",
      required: "ติ๊กช่องนี้เพื่อยืนยันว่าอ่านแล้ว",
    },
    problems: {
      exists: "สร้างบัญชีด้วยอีเมลนี้ไม่ได้ ถ้าเป็นอีเมลของคุณ ให้ลงชื่อเข้าใช้หรือส่งอีเมลกู้คืนรหัสผ่าน",
      invalidCredentials: "อีเมลหรือรหัสผ่านไม่ถูกต้อง",
      emailNotConfirmed: "ยืนยันอีเมลก่อน โดยเปิดข้อความที่เราส่งไปแล้วกดลิงก์ในนั้น",
      tooMany: "ลองหลายครั้งเกินไป รอสักครู่แล้วลองใหม่",
      invalidEmail: "อีเมลนี้ไม่ถูกต้อง",
      signUpClosed: "ขณะนี้ยังไม่เปิดรับบัญชีใหม่",
      offline: "ติดต่อระบบลงชื่อเข้าใช้ไม่ได้ ตรวจการเชื่อมต่อแล้วลองอีกครั้ง",
    },
    emailHint: "อีเมลของคลินิก",
    roles: { slp: "นักบำบัด / นักแก้ไขการพูด", admin: "ผู้ดูแลคลินิก", parent: "ผู้ปกครอง" },
    modes: { signIn: "ลงชื่อเข้าใช้", signUp: "สร้างบัญชี", invitationOnly: "เฉพาะผู้ได้รับเชิญ" },
    formLabel: "แบบฟอร์มลงชื่อเข้าใช้ด้วย Supabase",
    displayName: "ชื่อที่แสดง",
    displayNamePlaceholder: "ชื่อ-นามสกุลของคุณ",
    email: "อีเมล",
    password: "รหัสผ่าน",
    sendingRecovery: "กำลังส่งอีเมลกู้คืน...",
    sendRecovery: "ส่งอีเมลกู้คืนรหัสผ่าน",
    hidePassword: "ซ่อนรหัสผ่าน",
    showPassword: "แสดงรหัสผ่าน",
    signingIn: "กำลังลงชื่อเข้าใช้...",
    signIn: "ลงชื่อเข้าใช้พื้นที่ทำงานของคลินิก",
    signInLabel: "ลงชื่อเข้าใช้ด้วย Supabase",
    configMissing: "ยังไม่ได้ตั้งค่า Supabase สำหรับเบราว์เซอร์",
    configInvalid: "การตั้งค่า Supabase สำหรับเบราว์เซอร์ไม่ถูกต้อง",
    createAccountLabel: "สร้างบัญชี",
    creatingAccount: "กำลังสร้างบัญชี...",
    createAccount: "สร้างบัญชีคลินิก",
    orContinueWith: "หรือดำเนินการต่อด้วย",
    connectingGoogle: "กำลังเชื่อมต่อ Google...",
    continueWithGoogle: "ดำเนินการต่อด้วย Google",
    policyToggle: "รายละเอียดด้านความปลอดภัยและการเข้าถึง",
    publicNote: {
      stored: "บัญชีของคุณเก็บเคส ไฟล์เสียง บทถอดเสียง และรายงานที่คุณสร้าง ผู้ใช้คนอื่นเปิดดูไม่ได้ การถอนความยินยอมของเคสจะลบไฟล์เสียงของเคสนั้น",
      boundary: "PasaScope เป็นต้นแบบเพื่อการวิจัยและการศึกษา ใช้บรรยายตัวอย่างภาษาเท่านั้น ไม่ได้วินิจฉัย และยังไม่ผ่านการตรวจสอบทางคลินิกกับเด็กไทย",
      privacy: "ความเป็นส่วนตัว: เก็บอะไรและส่งไปที่ไหน",
    },
    policy: {
      invitationTitle: "เข้าใช้ได้เฉพาะผู้ได้รับเชิญ",
      invitationOn: "ปิดการสมัครสาธารณะ เฉพาะผู้ที่ตอบรับคำเชิญแล้วเท่านั้นจึงเข้าถึงบัญชีได้",
      invitationOff: "การตั้งค่าของระบบตอนนี้ยังไม่ได้บังคับให้เข้าใช้ได้เฉพาะผู้ได้รับเชิญ",
      mfaTitle: "MFA และการเข้าใช้แอป",
      mfaBefore: "หลังตอบรับคำเชิญ ต้องลงทะเบียน MFA แบบ TOTP",
      mfaMiddle: "เข้าได้เฉพาะหน้าจอ MFA และต้องเป็น",
      mfaAfter: "ก่อนเข้าขั้นตอนทางคลินิกหรือการดูแลระบบใดๆ",
      organizationTitle: "การเลือกองค์กรของเซสชัน",
      organizationBody:
        "ถ้ามีสมาชิกภาพที่ใช้งานอยู่หลายองค์กร ผู้ใช้ต้องเลือกองค์กรหนึ่งก่อนเข้าพื้นที่ทำงาน องค์กรที่ใช้ล่าสุดเป็นเพียงคำแนะนำเมื่อยังไม่ชัดเจนว่าจะเลือกองค์กรใด",
      recoveryTitle: "การกู้คืนและสถานะของระบบตอนนี้",
      recoveryBody: "การกู้คืนรหัสผ่านใช้ขั้นตอนรีเซ็ตของ Supabase และยังต้องผ่านด่านสมาชิกภาพและ MFA ก่อนเข้าใช้แอป",
      runtimeBody:
        "การลงชื่อเข้าใช้ในเบราว์เซอร์ขึ้นกับโปรเจกต์ Supabase และข้อกำหนด claim ที่ตั้งค่าไว้ ระบบจะยังไม่ให้เข้าพื้นที่ทำงานจนกว่าจะผ่านเงื่อนไขคำเชิญ สมาชิกภาพ MFA และองค์กรที่ใช้งาน",
      browserConfig: (status) => `การตั้งค่าเบราว์เซอร์: ${status}`,
    },
    status: {
      signUpSignedIn: "สร้างบัญชีแล้ว กำลังลงชื่อเข้าใช้...",
      signUpConfirmEmail: "สร้างบัญชีแล้ว หากระบบต้องการยืนยันอีเมล ให้เปิดข้อความในกล่องอีเมลเพื่อยืนยัน แล้วลงชื่อเข้าใช้",
      signInAccepted: "ลงชื่อเข้าใช้สำเร็จ กำลังตรวจองค์กรและ MFA",
      recoverySent: "ส่งอีเมลกู้คืนแล้ว หลังรีเซ็ตยังต้องมีสมาชิกภาพที่ตอบรับแล้วและ AAL2 จึงจะเข้าใช้แอปได้",
    },
    errors: {
      googleUnsupported: "การตั้งค่านี้ไม่รองรับ Google OAuth",
      googleNotEnabled:
        "ยังไม่ได้เปิดใช้ Google ใน Supabase Dashboard (ไปที่ Authentication > Providers > Google แล้วเปิดใช้พร้อมกรอก Client ID และ Secret)",
      googleFailed: "ลงชื่อเข้าใช้ด้วย Google ไม่สำเร็จ",
      configMissing: "ระบบนี้ยังไม่ได้ตั้งค่า Supabase สำหรับเบราว์เซอร์",
      signUpUnsupported: "การตั้งค่านี้ไม่รองรับการสมัคร",
      signUpFailed: "สมัครไม่สำเร็จ",
      signInFailed: "ลงชื่อเข้าใช้ไม่สำเร็จ",
      enterEmailFirst: "กรอกอีเมลที่ได้รับคำเชิญก่อน",
      recoveryFailed: "ขอกู้คืนรหัสผ่านไม่สำเร็จ",
    },
  },
});
