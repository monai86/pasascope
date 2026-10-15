import { defineMessages } from "@/i18n/messages";
import type { AuthProblem } from "@/lib/supabase-auth-error";

type SupabaseLoginCopy = {
  title: string;
  subtitle: string;
  optional: string;
  passwordHint: (minimum: number) => string;
  passwordTooShort: (minimum: number) => string;
  /** The acknowledgement beside the tick box, with the privacy page's link in the middle. */
  acknowledge: { before: string; link: string; after: string; required: string };
  problems: Record<Exclude<AuthProblem, "other" | "weakPassword">, string>;
  modes: { signIn: string; signUp: string };
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
  publicNote: { stored: string; boundary: string; privacy: string };
  status: {
    verifying: string;
    accountDeleted: string;
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
    title: "Sign in to PasaScope",
    subtitle: "Open your cases, transcripts and reports, or create an account to begin.",
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
    modes: { signIn: "Sign in", signUp: "Create account" },
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
    signIn: "Sign in",
    signInLabel: "Sign in with Supabase",
    configMissing: "Supabase browser config missing",
    configInvalid: "Supabase browser config invalid",
    createAccountLabel: "Create Account",
    creatingAccount: "Creating account...",
    createAccount: "Create account",
    orContinueWith: "Or continue with",
    connectingGoogle: "Connecting Google...",
    continueWithGoogle: "Continue with Google",
    publicNote: {
      stored: "Your account keeps the cases, recordings, transcripts and reports you create. Other users cannot open them. Withdrawing a case's consent removes its recordings.",
      boundary: "PasaScope is a research and education prototype. It describes a language sample; it does not diagnose, and it has no Thai clinical validation.",
      privacy: "Privacy: what is stored and where it goes",
    },
    status: {
      verifying: "Confirming your sign-in…",
      accountDeleted: "Your account and everything in it have been deleted.",
      signUpSignedIn: "Account created. Signing you in...",
      signUpConfirmEmail: "Check your inbox: open the message we sent to confirm your email, then sign in.",
      signInAccepted: "Signed in. Opening your workspace…",
      recoverySent: "If this email has an account, a recovery message is on its way.",
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
      enterEmailFirst: "Enter your email address first.",
      recoveryFailed: "Recovery request failed.",
    },
  },
  th: {
    title: "ลงชื่อเข้าใช้ PasaScope",
    subtitle: "เปิดเคส บทถอดเสียง และรายงานของคุณ หรือสร้างบัญชีเพื่อเริ่มใช้งาน",
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
    modes: { signIn: "ลงชื่อเข้าใช้", signUp: "สร้างบัญชี" },
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
    signIn: "ลงชื่อเข้าใช้",
    signInLabel: "ลงชื่อเข้าใช้ด้วย Supabase",
    configMissing: "ยังไม่ได้ตั้งค่า Supabase สำหรับเบราว์เซอร์",
    configInvalid: "การตั้งค่า Supabase สำหรับเบราว์เซอร์ไม่ถูกต้อง",
    createAccountLabel: "สร้างบัญชี",
    creatingAccount: "กำลังสร้างบัญชี...",
    createAccount: "สร้างบัญชี",
    orContinueWith: "หรือดำเนินการต่อด้วย",
    connectingGoogle: "กำลังเชื่อมต่อ Google...",
    continueWithGoogle: "ดำเนินการต่อด้วย Google",
    publicNote: {
      stored: "บัญชีของคุณเก็บเคส ไฟล์เสียง บทถอดเสียง และรายงานที่คุณสร้าง ผู้ใช้คนอื่นเปิดดูไม่ได้ การถอนความยินยอมของเคสจะลบไฟล์เสียงของเคสนั้น",
      boundary: "PasaScope เป็นต้นแบบเพื่อการวิจัยและการศึกษา ใช้บรรยายตัวอย่างภาษาเท่านั้น ไม่ได้วินิจฉัย และยังไม่ผ่านการตรวจสอบทางคลินิกกับเด็กไทย",
      privacy: "ความเป็นส่วนตัว: เก็บอะไรและส่งไปที่ไหน",
    },
    status: {
      verifying: "กำลังยืนยันข้อมูลการเข้าสู่ระบบ...",
      accountDeleted: "ลบบัญชีและข้อมูลทั้งหมดในบัญชีแล้ว",
      signUpSignedIn: "สร้างบัญชีแล้ว กำลังลงชื่อเข้าใช้...",
      signUpConfirmEmail: "เปิดกล่องอีเมล แล้วกดลิงก์ในข้อความที่เราส่งไปเพื่อยืนยันอีเมล จากนั้นลงชื่อเข้าใช้",
      signInAccepted: "ลงชื่อเข้าใช้แล้ว กำลังเปิดพื้นที่ทำงาน…",
      recoverySent: "ถ้าอีเมลนี้มีบัญชีอยู่ เราได้ส่งข้อความกู้คืนรหัสผ่านไปแล้ว",
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
      enterEmailFirst: "กรอกอีเมลก่อน",
      recoveryFailed: "ขอกู้คืนรหัสผ่านไม่สำเร็จ",
    },
  },
});
