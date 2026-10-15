# Offer two-step verification and account deletion to every account

Since invitation-only mode was removed, every account is personal and nobody
administers it, so both controls belong to the account holder. Two-step
verification with an authenticator app (Supabase TOTP) is optional and is
turned on and off in Settings › Privacy & Security; once an account has a
verified factor, the web app asks for the code after every sign-in and the API
refuses any request made with an `aal1` session of that account. A token does
not say whether its account has a factor, so the API asks Supabase Auth's admin
API for an `aal1` session and keeps the answer for 60 seconds; when Supabase
cannot answer, the request fails with 503 instead of being let through. The
check needs the project's service role key, which the API already holds for the
recording backup; an API without it reports both features as unavailable in
`GET /settings`, and the web app does not offer them, so the browser never
promises a protection the server does not enforce. There are no recovery codes:
an account holder who loses the app asks the operator, who removes the factor in
the Supabase dashboard.

`DELETE /api/v1/account` deletes the caller's account in three steps, from what
is hardest to retry to what is easiest: the stored recordings (the backup copy
first), then every row of the workspace, then the Supabase Auth user. If a
recording cannot be removed nothing else is touched (503); if the Auth user
cannot be removed the records are already gone and a repeat finishes the job
(502). The workspace's audit events and reports go with it; one audit event
with no content records that the account was deleted. This replaces, for
personal accounts, the clinic rule in `docs/SECURITY.md` that deletion waits for
a reviewed privacy request and keeps audit and sign-off evidence: there is no
reviewer any more, and the privacy page promises that everything goes. The web
app asks the person to type the account's email before it sends the request.
