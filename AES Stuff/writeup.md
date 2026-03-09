# AES-ECB Oracle Write-Up

## Challenge

The service exposes an encryption oracle with this behavior:

- We control an input string `input`.
- The server appends a secret flag to our input.
- The combined plaintext is padded.
- The server encrypts the result with AES under a fixed unknown key.
- The ciphertext is returned as hex.

Conceptually, the service does this:

```text
ciphertext = AES-ECB_k(Pad(input || flag))
```

The endpoint used in this solve was:

```text
https://aes-challenge-thingy.vercel.app/api/oracle
```

The goal is to recover `flag` without knowing the key.

## Why This Is Broken

ECB mode is deterministic: the same 16-byte plaintext block always encrypts to the same 16-byte ciphertext block under the same key.

That matters here because:

- the key is fixed,
- we can choose arbitrary plaintext,
- our plaintext is placed immediately before the secret,
- and the service returns the raw encryption result.

That is exactly the setup needed for the classic byte-at-a-time ECB decryption attack.

## Step 1: Find the Correct Request Format

The oracle did not accept a plain `GET`, and a `POST` without the expected form data returned:

```json
{"error":"Invalid input"}
```

The working request format was:

```bash
wsl bash -lc "curl -sS -X POST \
  https://aes-challenge-thingy.vercel.app/api/oracle \
  -H 'content-type: application/x-www-form-urlencoded' \
  --data 'input=A'"
```

A valid response looked like this:

```json
{"ciphertext":"18fd95136877ad37cccd9272ef4b840312080649b992f7458ad4c78cac2f24bf0791fcecb5e0d1811734593e42510c60"}
```

So the oracle input parameter is the form field `input`.

## Step 2: Determine the Block Size and Secret Length

I measured the ciphertext length for inputs of increasing size.

Observed values:

- `len(oracle("")) = 48` bytes
- the first time the ciphertext length increased was when I sent `8` bytes of input
- at that point the ciphertext length became `64` bytes

That tells us two things.

### Block size

The ciphertext grew by `16` bytes, so the cipher is operating on 16-byte blocks. That is consistent with AES.

### Secret length

With no user input, the padded plaintext length is `48`.

If adding `8` bytes is the first time we need one more block, then the original secret was exactly `8` bytes short of that boundary:

```text
secret_length = 48 - 8 = 40
```

So the hidden suffix is 40 bytes long.

## Step 3: Confirm ECB Mode

To distinguish ECB from modes like CBC, I sent a long run of identical bytes:

```text
"A" * 64
```

The first four ciphertext blocks were identical:

```text
5301d1251af08a9ea49cf85982d8df6e
5301d1251af08a9ea49cf85982d8df6e
5301d1251af08a9ea49cf85982d8df6e
5301d1251af08a9ea49cf85982d8df6e
```

That is the fingerprint of ECB: identical plaintext blocks produced identical ciphertext blocks.

At this point the service behavior is effectively confirmed as:

```text
AES-ECB with 16-byte blocks and standard block padding
```

The exact key size and exact padding scheme do not matter for the attack.

## Step 4: Byte-at-a-Time ECB Decryption

Now the real exploit.

Because the oracle encrypts:

```text
input || flag
```

we can shift the unknown flag bytes into positions we choose.

### Recovering the first unknown byte

AES works on 16-byte blocks, so first I submit 15 known bytes:

```text
AAAAAAAAAAAAAAA
```

The first block becomes:

```text
AAAAAAAAAAAAAAA?
```

where `?` is the first byte of the secret flag.

Call the resulting first ciphertext block the `target`.

Now I build a dictionary by trying every possible candidate for `?`:

```text
AAAAAAAAAAAAAAA + candidate
```

For each candidate, I encrypt that input and record the first ciphertext block.

When a candidate produces the same ciphertext block as `target`, that candidate must be the correct byte.

### Recovering later bytes

Suppose I already know the first `i` bytes of the flag.

To recover byte `i`, I choose:

```text
pad_len = 15 - (i mod 16)
prefix = "A" * pad_len
```

This moves the next unknown byte to the end of some block.

Then:

1. Query the oracle with just `prefix`.
2. Extract the block containing the unknown byte.
3. For each candidate character `c`, query the oracle with:

```text
prefix + recovered + c
```

4. Compare the same block index.
5. The candidate that matches is the next byte of the flag.

Repeat until all 40 bytes are recovered.

## Why the Full Recovered Prefix Matters

There is one implementation detail that is easy to get wrong.

For the first block, it is enough to think in terms of the last 15 known bytes. But for later blocks, the comparison must still happen at the correct block index, so the probe plaintext must include the full recovered prefix:

```text
prefix + recovered + candidate
```

not just:

```text
last_15_bytes + candidate
```

If you drop the earlier recovered bytes, the target byte shifts into a different block and the dictionary comparison fails once you move past block 0.

That was the only bug I hit during the live solve.

## Final Exploit Script

This is the cleaned solver used for the write-up. It is also saved locally as `solve.py`.

```python
#!/usr/bin/env python3
import json
import string
import sys
import urllib.parse
import urllib.request


URL = "https://aes-challenge-thingy.vercel.app/api/oracle"
BLOCK_SIZE = 16


def oracle(user_input: str) -> bytes:
    data = urllib.parse.urlencode({"input": user_input}).encode()
    request = urllib.request.Request(
        URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode())
    return bytes.fromhex(payload["ciphertext"])


def detect_secret_length() -> int:
    base_len = len(oracle(""))
    for added in range(1, BLOCK_SIZE + 1):
        if len(oracle("A" * added)) > base_len:
            return base_len - added
    raise RuntimeError("failed to detect secret length")


def recover_flag() -> bytes:
    secret_len = detect_secret_length()
    candidates = (
        string.ascii_uppercase
        + string.ascii_lowercase
        + string.digits
        + "{}_!@#$%^&*()-=+[]:;,.?/\\|~`'\"<> "
    )
    recovered = bytearray()

    print(f"[+] block size: {BLOCK_SIZE}")
    print(f"[+] secret length: {secret_len}")

    for index in range(secret_len):
        pad_len = BLOCK_SIZE - 1 - (index % BLOCK_SIZE)
        prefix = "A" * pad_len
        block_index = index // BLOCK_SIZE
        block_start = block_index * BLOCK_SIZE
        block_end = block_start + BLOCK_SIZE
        target = oracle(prefix)[block_start:block_end]

        match = None
        for candidate in candidates:
            probe = (prefix.encode() + recovered + candidate.encode()).decode("latin-1")
            block = oracle(probe)[block_start:block_end]
            if block == target:
                recovered.append(ord(candidate))
                match = candidate
                break

        if match is None:
            raise RuntimeError(
                f"failed to recover byte {index}; recovered so far: {recovered!r}"
            )

        print(f"[+] {index + 1:02d}/{secret_len}: {recovered.decode('ascii')}", flush=True)

    return bytes(recovered)


def main() -> int:
    try:
        flag = recover_flag()
    except Exception as exc:
        print(f"[-] {exc}", file=sys.stderr)
        return 1

    print(f"[+] flag: {flag.decode('ascii')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Running It from WSL

Because the task explicitly asked to use WSL, I ran the local solver from the Windows workspace through WSL like this:

```bash
wsl bash -lc "python3 -u '/mnt/d/CRYPTONITE/AES Stuff/solve.py'"
```

The script recovered the secret one byte at a time and ended with:

```text
[+] flag: TACHYON{w3lp_3cp_1s_bu5t3ed_L0l_d23d3cf}
```

## Final Flag

```text
TACHYON{w3lp_3cp_1s_bu5t3ed_L0l_d23d3cf}
```

## Takeaway

AES itself was not the problem. The failure was using ECB with:

- a fixed key,
- attacker-controlled input,
- a secret appended directly after that input,
- and raw encryption oracle access.

That combination makes the secret recoverable without ever learning the key.
