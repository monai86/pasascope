# Present the therapist workflow as a guided conversation without a language model

PasaScope's public web app moves from a step-by-step workbench to a chat-first
shell: a home screen that asks what to do, and one conversation per session at
`/sessions/{sessionId}?view=chat` that carries case choice, caregiver consent,
audio intake, transcription status, speaker assignment and descriptive language
measures. The conversation is a deterministic projection of backend session
state, not a stored message log, so the backend stays the source of truth and a
reload rebuilds the same thread. No language model reads or writes messages:
system lines come from workflow state, the therapist answers with quick replies,
typed text on Home finds a case and typed text in a session is saved as a
session note, and no command is ever inferred from typed text. Line-by-line
transcript editing and report editing remain full pages opened from the
conversation. The shell is the interface whenever the API runs with public
sign-up and open review gates. An API that still enforces review gates keeps
the existing workbench, whose screens carry the attestation and sign-off steps
the conversation does not have, until that path is removed; a build with
`NEXT_PUBLIC_CHAT_SHELL=false` keeps the workbench everywhere. A language-model
layer, if added later, must be opt-in, default off, and bound by the same
clinical-safety and provenance rules as AI report drafting.
