# Glitched - Write-up

## Summary

The challenge gives a public RSA key, a ciphertext, and two suspicious outputs:

- `n`: RSA modulus
- `e`: public exponent
- `c`: ciphertext
- `s1`
- `s2`

The key observation is that `s1` is a full RSA signature, while `s2` is not another full signature. Instead, `s2` is the CRT residue of that signature modulo one prime factor of `n`.

That leak is enough to factor `n`, recover the private key, decrypt the ciphertext, and obtain the flag.

Flag:

`TACHYON{f4ulty_crt_l3eaks_th3rr_k3y!}`

---

## Given Data

```text
n = 150027296120774783226809267193736779553324913768816146206789764139416634824465087029424160668822746906678784145486278607159022171323793059598021282185186158099538631361984491563332751767210663181705625045298068512624768473686330875450781870803915018424789368032875080371517806994596340135890205692368415033023
e = 65537
c = 64333748676195340982665158878679548906756197385349872894794373163425773604508455519380238359978386590619308579935696203377815603414143375785272938717227647037611061818609679817050233420643728500628438080811909558436079149300885437961844571720703495368629368718870438488205337304990147082622103716010612327309
s1 = 97373835871218809554176384535129292787642672517949132880901697388844753063021191909807337413968889120737197620676960589962462531460492240581076149678341716280330188501588877602788009208686170841542316245596480070067181488057075535252138999084101100591888392102436982252812385520522990860083098514360964434434
s2 = 3135986448272973480541070408566279203202280902419276805632351783435536778914708172331997550330858374164485332708713690810869133296847577360658505941910101
```

---

## Step 1: Recognize What Looks Wrong

`n` is a 1024-bit RSA modulus, so a normal RSA signature should also be about 1024 bits.

`s1` is indeed 1024 bits.

`s2`, however, is only about 510 bits. That is too small to look like a normal full RSA signature modulo `n`, but it is exactly the size we would expect for a value modulo one prime factor of `n` (roughly 512 bits).

That strongly suggests:

- `s1` is a full signature modulo `n`
- `s2` is a residue modulo one of the private CRT primes

---

## Step 2: Why a CRT Leak Breaks RSA

RSA implementations often use CRT for speed.

Instead of computing:

```text
s = m^d mod n
```

they compute:

```text
sp = m^d mod p
sq = m^d mod q
```

and then recombine `sp` and `sq` into the full signature `s` modulo `n`.

If an implementation accidentally leaks one branch directly, or a fault causes an inconsistent CRT output, then the relation

```text
s = sp (mod p)
```

still holds.

So:

```text
p | (s - sp)
```

which means:

```text
gcd(s - sp, n) = p
```

This is the core of the attack.

In this challenge:

- `s1` plays the role of the full signature `s`
- `s2` plays the role of the leaked CRT residue `sp`

So we try:

```text
gcd(s1 - s2, n)
```

---

## Step 3: Factor the Modulus

Computing the GCD gives:

```text
p = gcd(s1 - s2, n)
  = 12491793414438097271596489009810161970902125262355249004038020327445777509933133702994271264467749179335687227656424237623086625743588600891570624024796217
```

Then:

```text
q = n / p
  = 12010068622122124131676819326782071788947894576837692488698613582426708045879262064154921741262538482264483860447279925138217427455280415428913021191809719
```

Check:

```text
p * q = n
```

So the modulus is fully factored.

An extra sanity check confirms the interpretation:

```text
s2 = s1 mod p
```

So `s2` is literally the `mod p` residue of the full signature.

---

## Step 4: Recover the Private Key

Now compute Euler's totient:

```text
phi(n) = (p - 1)(q - 1)
```

Then compute the private exponent:

```text
d = e^(-1) mod phi(n)
```

Once `d` is known, decrypt the ciphertext:

```text
m = c^d mod n
```

This gives:

```text
m = 41901935913912043678304779529559025578536544413568182491698078181377801797618812830949757
```

Hex:

```text
54414348594f4e7b6634756c74795f6372745f6c3365616b735f74683372725f6b3379217d
```

ASCII:

```text
TACHYON{f4ulty_crt_l3eaks_th3rr_k3y!}
```

---

## Step 5: Relationship Between the Values

There is one more useful observation:

```text
pow(s1, e, n) = m
```

So `s1` is a valid RSA signature on the same message that `c` encrypts.

Also, because `s2 = s1 mod p`, we have:

```text
pow(s2, e, p) = m mod p
```

This is exactly what we expect if `s2` is the `mod p` branch of an RSA-CRT signature.

So the two outputs are different because they are not the same kind of object:

- `s1` is the fully recombined signature modulo `n`
- `s2` is only the partial CRT result modulo `p`

That partial leak is enough to destroy the secrecy of the RSA private key.

---

## WSL Solve Script

The following script reproduces the full solve under WSL:

```bash
wsl python3 - <<'PY'
from math import gcd

n = 150027296120774783226809267193736779553324913768816146206789764139416634824465087029424160668822746906678784145486278607159022171323793059598021282185186158099538631361984491563332751767210663181705625045298068512624768473686330875450781870803915018424789368032875080371517806994596340135890205692368415033023
e = 65537
c = 64333748676195340982665158878679548906756197385349872894794373163425773604508455519380238359978386590619308579935696203377815603414143375785272938717227647037611061818609679817050233420643728500628438080811909558436079149300885437961844571720703495368629368718870438488205337304990147082622103716010612327309
s1 = 97373835871218809554176384535129292787642672517949132880901697388844753063021191909807337413968889120737197620676960589962462531460492240581076149678341716280330188501588877602788009208686170841542316245596480070067181488057075535252138999084101100591888392102436982252812385520522990860083098514360964434434
s2 = 3135986448272973480541070408566279203202280902419276805632351783435536778914708172331997550330858374164485332708713690810869133296847577360658505941910101

p = gcd(s1 - s2, n)
q = n // p
phi = (p - 1) * (q - 1)
d = pow(e, -1, phi)
m = pow(c, d, n)

hex_m = hex(m)[2:]
if len(hex_m) % 2:
    hex_m = "0" + hex_m

print("p =", p)
print("q =", q)
print("s2 == s1 mod p ->", s2 == s1 % p)
print("m =", m)
print("hex =", hex_m)
print("flag =", bytes.fromhex(hex_m).decode())
PY
```

Expected output:

```text
flag = TACHYON{f4ulty_crt_l3eaks_th3rr_k3y!}
```

---

## Final Explanation

The challenge is built around a CRT leak in RSA signing.

The important idea is that a full CRT-based RSA signature is assembled from two smaller computations:

- one modulo `p`
- one modulo `q`

If the server ever exposes one branch directly, or returns an inconsistent CRT result, then the difference between the full signature and the leaked branch is divisible by one of the secret primes. Taking a GCD with `n` immediately factors the modulus.

That is exactly what happened here:

```text
gcd(s1 - s2, n) = p
```

Once `p` and `q` are known, RSA is finished:

- compute `phi(n)`
- compute `d`
- decrypt `c`
- decode the plaintext

Result:

`TACHYON{f4ulty_crt_l3eaks_th3rr_k3y!}`
