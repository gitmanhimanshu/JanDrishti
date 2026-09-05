# Security and privacy

## Authentication is not verification

Signing in with Google proves control of a Google account. It proves nothing
about a profession, an employer, a rank or expertise. These are separate systems
that share nothing but a user id.

```
Google OAuth  →  a JanDrishti account          (identity)
                       │
                       │  a wholly separate, reviewed process
                       ▼
ProfessionalVerification  →  document  →  human review  →  badge
```

`is_professionally_verified` is written in exactly one place:
`ReviewVerificationUseCase`, as the result of a human decision. Nothing
automated can grant it.

## Sessions

| | Access token | Refresh token |
| --- | --- | --- |
| Form | Stateless JWT | Opaque random string |
| Lifetime | 30 minutes | 30 days |
| Storage | `sessionStorage` (browser) | Hashed (SHA-256) in the database |
| Revocable | No (short-lived by design) | Yes, individually or by family |

**Rotation and replay detection.** Every refresh issues a new token and revokes
the old one. Presenting an already-rotated token means either a race or theft;
we cannot tell which, so the whole token family is revoked. The legitimate user
signs in again; an attacker gets nothing.

**Roles come from the database.** A token carries a role only as a hint for the
client UI. Every permission check reads the role from the user row, so a
revoked role takes effect on the next request. There is a test for this:
`test_role_in_the_token_does_not_grant_access` forges an ADMIN token for a
citizen and asserts a 403.

## Authorization

Three layers, all server-side:

1. **View permission** — is this actor allowed to attempt this at all?
2. **Object permission** — is this actor allowed to act on *this* object?
3. **Domain rule** — is this action legal given the object's current state?

The second layer is where IDOR lives. A government official has a role, but
`_assert_department_scope` also checks their `DepartmentMembership` against the
problem's department path. Without it, any official could close any issue in the
country.

```python
allowed = DepartmentMembership.objects.filter(user=user, is_active=True) \
                                      .values_list("department__path", flat=True)
if not any(path == dept or dept.startswith(f"{path}/") for path in allowed):
    raise PermissionDeniedError("This problem belongs to another department.")
```

**Privilege escalation is structurally impossible from the client.** The
onboarding serializer's role choices are restricted to `CITIZEN` and
`PROFESSIONAL`; `GOVERNMENT_OFFICIAL`, `MODERATOR` and `ADMIN` are not in the
enum it accepts. The profile serializer does not include `role` or
`is_professionally_verified` as writable fields.

## Aadhaar

The optional fallback for people with no suitable professional document.

**What is stored:** the provider's opaque eKYC reference, the last four digits
(so a reviewer can confirm with the applicant), the provider name, a timestamp.

**What is never stored, anywhere:** the number itself. There is no field for it.
`test_aadhaar_number_is_not_a_field_anywhere_on_the_model` asserts this against
the model's field list, so adding one would fail CI.

Aadhaar is:

- never mandatory — it is one of several verification routes
- never a login credential
- never the primary key
- never in a URL, a public serializer, or an API response
- redacted from logs by pattern, not by convention: `\d{4}[ -]?\d{4}[ -]?\d{4}`
  is scrubbed by a logging filter before any handler sees it

## Verification documents

- Uploaded through a separate endpoint that forces `is_private=True`, so a
  client cannot forget to ask for privacy.
- The upload response contains an id and **no URL**. There is nothing to leak.
- Reading one requires the moderator role and produces a signed URL valid for
  five minutes.
- Every read writes a `DocumentAccessLog` row *and* an audit record, before the
  URL is issued — so the record exists even if the reviewer never opens it.
- Purged on a schedule (`VERIFICATION_DOCUMENT_RETENTION_DAYS`, default 180
  days after the decision). Privacy by design is a scheduled job, not an
  intention.

## Uploads

Validated server-side against the declared type *and* the actual bytes:

```python
MAGIC_SIGNATURES = {"image/jpeg": (b"\xff\xd8\xff",), "image/png": (b"\x89PNG\r\n\x1a\n",), ...}
```

A PHP script renamed `photo.jpg` is rejected because its header is not a JPEG
header. Size limits are enforced per type (10 MB image, 100 MB video, 20 MB
document) and read from the reported size, not by buffering the file.

Attachment re-checks ownership: you may only attach media you uploaded, which
stops one user stapling another user's evidence onto their own report.

## Evidence integrity

Uploaded is not verified. The distinction is enforced at three levels:

- **Schema** — `verification_status` defaults to `UPLOADED`.
- **Code** — no citizen-facing path can set `VERIFIED`.
- **Interface** — the badge says "Uploaded, not verified" in plain words, not by
  a subtle shade of grey.

## What AI does not decide

Automated tools assist with categorising, department routing, duplicate
detection, summarising and translation. They never determine:

- whether corruption occurred
- whether a person is guilty
- whether evidence is authentic
- whether an official has done wrong
- a professional verification outcome
- any legal conclusion

Duplicate detection proposes; a moderator can merge or detach, and every such
action is audited.

## Logging

A redaction filter runs before any handler. It scrubs by key name
(`token`, `secret`, `client_secret`, `aadhaar*`, `document_url`, …) and by
pattern (Bearer tokens, JWT-shaped strings, Aadhaar-shaped digits), recursively
through nested structures.

Placing this in a filter rather than at call sites is deliberate: relying on
every future call site to remember is how secrets end up in logs.

## Production hardening

`config/settings/production.py` refuses to boot if:

- `SECRET_KEY` is missing or still the development default
- `DATABASE_URL` is unset or not PostgreSQL
- `REDIS_URL` is unset

A misconfigured deploy fails loudly rather than quietly serving an insecure
site. HSTS, `SECURE_SSL_REDIRECT`, secure cookies, `X-Frame-Options: DENY`,
nosniff and a strict referrer policy are all on.

## Tested

`backend/tests/test_security.py` — 37 tests covering privilege escalation, token
forgery and expiry, banned accounts, IDOR on notifications and media, upload
type confusion and size limits, Aadhaar non-storage, private document handling,
self-review prevention, double-decision prevention, log redaction, and the
funding kill switch.
