#!/usr/bin/env python3
import json
import string
import sys
import urllib.parse
import urllib.request


URL = "https://aes-challenge-thingy.vercel.app/api/oracle"
BLOCK_SIZE = 16
KNOWN_PREFIX = b""


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
    recovered = bytearray(KNOWN_PREFIX)

    print(f"[+] block size: {BLOCK_SIZE}")
    print(f"[+] secret length: {secret_len}")
    if recovered:
        print(f"[+] resuming from: {recovered.decode('ascii')}")

    for index in range(len(recovered), secret_len):
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
