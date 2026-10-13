/**
 * What went wrong with a sign-in or sign-up request, as a short list the form
 * has words for. The auth service's own message is never shown: it is in
 * English only, and some of its messages say whether an email has an account.
 */
export type AuthProblem =
  | "exists"
  | "weakPassword"
  | "invalidCredentials"
  | "emailNotConfirmed"
  | "tooMany"
  | "invalidEmail"
  | "signUpClosed"
  | "offline"
  | "other";

const BY_CODE: Record<string, AuthProblem> = {
  user_already_exists: "exists",
  email_exists: "exists",
  weak_password: "weakPassword",
  invalid_credentials: "invalidCredentials",
  email_not_confirmed: "emailNotConfirmed",
  over_request_rate_limit: "tooMany",
  over_email_send_rate_limit: "tooMany",
  email_address_invalid: "invalidEmail",
  validation_failed: "invalidEmail",
  signup_disabled: "signUpClosed",
  email_provider_disabled: "signUpClosed",
};

// Older responses carry no code, only a message.
const BY_MESSAGE: Array<[RegExp, AuthProblem]> = [
  [/already registered|already exists/i, "exists"],
  [/password should be|weak password/i, "weakPassword"],
  [/invalid login credentials/i, "invalidCredentials"],
  [/email not confirmed/i, "emailNotConfirmed"],
  [/rate limit|too many/i, "tooMany"],
  [/invalid email|email address .* invalid/i, "invalidEmail"],
  [/signups? not allowed|signup is disabled/i, "signUpClosed"],
  [/failed to fetch|networkerror|load failed|network request failed/i, "offline"],
];

export function classifyAuthError(error: unknown): AuthProblem {
  if (!error || typeof error !== "object") return "other";
  const { code, status, message } = error as { code?: unknown; status?: unknown; message?: unknown };
  if (typeof code === "string" && BY_CODE[code]) return BY_CODE[code];
  if (status === 429) return "tooMany";
  if (error instanceof TypeError) return "offline";
  const text = typeof message === "string" ? message : "";
  return BY_MESSAGE.find(([pattern]) => pattern.test(text))?.[1] ?? "other";
}
