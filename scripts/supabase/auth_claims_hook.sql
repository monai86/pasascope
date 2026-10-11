-- PasaScope access claims for Supabase Auth.
--
-- The API authorizes every request from claims in the signed access token
-- (see docs/SUPABASE_AUTH_CONTRACT.md). Nothing else writes those claims, so
-- without this hook every real Supabase user is rejected by the API.
--
-- Run once against the Supabase database that holds the API tables (after the
-- API migrations), then enable it in the dashboard:
--   Authentication -> Hooks -> Customize Access Token (JWT) Claims
--   -> Postgres function -> public.pasascope_access_token_hook
--
-- The hook runs on every token issue and refresh. A user's organization
-- access therefore follows the membership tables: revoke a membership and the
-- next token (at most one access-token lifetime later) no longer carries it.

create or replace function public.pasascope_access_token_hook(event jsonb)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  claims jsonb := coalesce(event -> 'claims', '{}'::jsonb);
  subject text := event ->> 'user_id';
  -- Access claims are always rebuilt here; never trust what is already there.
  app_meta jsonb := coalesce(claims -> 'app_metadata', '{}'::jsonb)
    - 'organization_id' - 'role' - 'membership_active' - 'invitation_status'
    - 'organizations' - 'organization_memberships' - 'break_glass';
  memberships jsonb;
  membership_count integer;
  invitation_accepted boolean;
begin
  select
    coalesce(
      jsonb_agg(
        jsonb_build_object(
          'organization_id', m.organization_id,
          'name', coalesce(o.name, m.organization_id),
          'role', m.role,
          'active', true
        )
        order by m.created_at, m.organization_id
      ),
      '[]'::jsonb
    ),
    count(*)
  into memberships, membership_count
  from public.organization_memberships m
  left join public.organizations o on o.organization_id = m.organization_id
  where m.user_id = subject
    and m.active
    and m.role in ('therapist', 'clinical_supervisor', 'org_admin');

  if membership_count = 0 then
    -- Signed in, but a member of nothing: issue a token with no access claims.
    return jsonb_set(event, '{claims}', jsonb_set(claims, '{app_metadata}', app_meta));
  end if;

  -- Invitation gate: satisfied by an accepted invitation, or by being an
  -- organization admin (admins are provisioned directly, see
  -- pasascope_provision_first_admin, and are the ones who issue invitations).
  select
    exists (
      select 1
      from public.organization_invitations i
      where i.accepted_user_id = subject and i.status = 'accepted'
    )
    or exists (
      select 1
      from public.organization_memberships m
      where m.user_id = subject and m.active and m.role = 'org_admin'
    )
  into invitation_accepted;

  app_meta := app_meta
    || jsonb_build_object(
      'membership_active', true,
      'invitation_status', case when invitation_accepted then 'accepted' else 'pending' end,
      'organizations', memberships
    );

  if membership_count = 1 then
    -- One organization: it is the active context. With several, the client
    -- must select one explicitly (X-Organization-Id) and no default is implied.
    app_meta := app_meta
      || jsonb_build_object(
        'organization_id', memberships -> 0 ->> 'organization_id',
        'role', memberships -> 0 ->> 'role'
      );
  end if;

  return jsonb_set(event, '{claims}', jsonb_set(claims, '{app_metadata}', app_meta));
end;
$$;

-- Only Supabase Auth may call the hook.
revoke execute on function public.pasascope_access_token_hook(jsonb) from public;
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke execute on function public.pasascope_access_token_hook(jsonb) from anon;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke execute on function public.pasascope_access_token_hook(jsonb) from authenticated;
  end if;
  if exists (select 1 from pg_roles where rolname = 'supabase_auth_admin') then
    grant usage on schema public to supabase_auth_admin;
    grant execute on function public.pasascope_access_token_hook(jsonb) to supabase_auth_admin;
  end if;
end;
$$;


-- First organization admin.
--
-- Every admin route requires a stored org-admin membership, and the hook only
-- issues an org_admin claim from such a row. The first admin of a new
-- organization is therefore created here by the platform operator, from the
-- SQL editor (service role), never through the public API:
--
--   select public.pasascope_provision_first_admin(
--     'clinic_001', 'Example Clinic', '<auth.users id of the admin>', 'Admin Name'
--   );
--
-- It refuses to run if the organization already has an active admin.
create or replace function public.pasascope_provision_first_admin(
  p_organization_id text,
  p_organization_name text,
  p_user_id text,
  p_display_name text
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  new_membership_id text;
begin
  if coalesce(btrim(p_organization_id), '') = '' or coalesce(btrim(p_user_id), '') = '' then
    raise exception 'organization id and user id are required';
  end if;
  if exists (
    select 1
    from public.organization_memberships m
    where m.organization_id = p_organization_id and m.role = 'org_admin' and m.active
  ) then
    raise exception 'organization % already has an active admin; use the admin API', p_organization_id;
  end if;

  insert into public.organizations (organization_id, name, pilot_mode, created_at)
  values (p_organization_id, coalesce(nullif(btrim(p_organization_name), ''), p_organization_id), false, now())
  on conflict (organization_id) do nothing;

  insert into public.user_profiles (user_id, display_name, created_at)
  values (p_user_id, coalesce(nullif(btrim(p_display_name), ''), p_user_id), now())
  on conflict (user_id) do nothing;

  -- Update-then-insert rather than ON CONFLICT, so this also works on a
  -- database that predates the (organization_id, user_id) unique constraint.
  update public.organization_memberships m
  set role = 'org_admin', active = true
  where m.organization_id = p_organization_id and m.user_id = p_user_id
  returning m.membership_id into new_membership_id;
  if not found then
    new_membership_id := 'mbr_' || substr(md5(p_organization_id || ':' || p_user_id), 1, 10);
    insert into public.organization_memberships (membership_id, organization_id, user_id, role, active, created_at)
    values (new_membership_id, p_organization_id, p_user_id, 'org_admin', true, now());
  end if;

  insert into public.audit_logs (audit_id, organization_id, actor_id, action, target_id, outcome, correlation_id, message, "timestamp")
  values (
    'audit_' || substr(md5(random()::text || clock_timestamp()::text), 1, 10),
    p_organization_id,
    'platform_operator',
    'membership.bootstrap',
    new_membership_id,
    'success',
    'sql-provision',
    'First organization admin membership recorded.',
    now()
  );

  return new_membership_id;
end;
$$;

revoke execute on function public.pasascope_provision_first_admin(text, text, text, text) from public;
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke execute on function public.pasascope_provision_first_admin(text, text, text, text) from anon;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke execute on function public.pasascope_provision_first_admin(text, text, text, text) from authenticated;
  end if;
end;
$$;
