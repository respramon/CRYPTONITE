# RSA Decipher Write-up

## Challenge Summary

The file `challenge.txt` gives three RSA parameters:

- `n`: the modulus
- `c`: the ciphertext
- `e = 18`: the public exponent

The goal is to recover the plaintext flag.

## Key Observation

This challenge is vulnerable because the public exponent is very small and the plaintext was encrypted without padding.

For textbook RSA encryption:

```text
c = m^e mod n
```

If the plaintext integer `m` is small enough that:

```text
m^e < n
```

then modular reduction never happens, so the ciphertext is actually:

```text
c = m^e
```

over the integers, not just modulo `n`.

That means decryption becomes trivial:

```text
m = e-th_root(c)
```

No factorization of `n` is needed.

## Why This Works Here

From the challenge file:

```text
e = 18
```

That is the entire weakness. We can test whether `c` is an exact 18th power.

Computing the integer 18th root of `c` gives:

```text
m = 3449838678209581387703926389797474809112932842366507927778972423831411666498167165
```

Verification:

```text
m^18 == c
```

This confirms that the ciphertext never wrapped modulo `n`, so the plaintext is directly recoverable from the integer root.

## Convert the Plaintext Integer to Bytes

After recovering `m`, convert it from a big-endian integer into bytes:

```text
74616368796f6e7b5224345f6372797074306772347068795f69245f65347379217d
```

Decoding those bytes as ASCII gives:

```text
tachyon{R$4_crypt0gr4phy_i$_e4sy!}
```

## Solver

The following Python script solves the challenge directly from `challenge.txt` without any external libraries:

```python
from pathlib import Path
import re


def iroot(n: int, k: int) -> int:
    lo, hi = 0, 1
    while hi ** k <= n:
        hi *= 2

    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if mid ** k <= n:
            lo = mid
        else:
            hi = mid

    return lo


data = Path("challenge.txt").read_text()
vals = dict(re.findall(r"([nce])=(\d+)", data))

n = int(vals["n"])
c = int(vals["c"])
e = int(vals["e"])

m = iroot(c, e)
assert m ** e == c
assert m ** e < n

flag = m.to_bytes((m.bit_length() + 7) // 8, "big").decode()
print(flag)
```

## Output

```text
tachyon{R$4_crypt0gr4phy_i$_e4sy!}
```

## Final Flag

```text
tachyon{R$4_crypt0gr4phy_i$_e4sy!}
```

## Notes

- This is a classic low-exponent textbook RSA failure.
- Proper padding schemes such as OAEP prevent this kind of attack.
- Strictly speaking, `e = 18` is not a standard valid RSA public exponent for a normal modulus made from two odd primes, because it would not be coprime to `phi(n)`. That detail does not matter for solving this challenge, because the ciphertext is already an exact 18th power over the integers.
