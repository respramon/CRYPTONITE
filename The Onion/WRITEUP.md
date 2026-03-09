# The Onion Write-Up

## Challenge Summary

The challenge dropped a single file in the working directory:

```text
layer_100.zip
```

The clue was:

> "This one you'll just have to peel like an onion to get the flag lol."

That strongly suggested a stack of nested archives or compressed files, where each extracted layer reveals the next one.

## Initial Recon

I started by listing the directory contents:

```powershell
Get-ChildItem -Force
```

That showed only one file:

```text
layer_100.zip
```

To inspect the first layer from Linux, I used `wsl`:

```powershell
wsl --cd "/mnt/d/CRYPTONITE/The Onion" unzip -l layer_100.zip
```

The output showed that the ZIP contained:

```text
layer_100.tar
```

So the first layer was:

```text
ZIP -> TAR
```

At that point, the challenge structure was clear: keep unpacking until the final payload appears.

## Why WSL Was the Right Choice

This challenge is much easier to solve in Linux because the standard archive tools are already available and scriptable:

- `unzip`
- `tar`
- `gunzip`
- `bunzip2`
- `unxz`
- `file`
- `base64`

Using `wsl` also avoids the friction of handling several archive formats manually in Windows tools.

## Extraction Strategy

Instead of unpacking every layer by hand, I wrote a small Bash helper script and ran it through `wsl`.

The approach was:

1. Copy the starting archive into a temporary directory.
2. Identify the current file type with `file --mime-type`.
3. Extract or decompress it based on the detected type.
4. Remove the previous layer.
5. Repeat until the current file is plain text.
6. If the result looks encoded, decode it.

Using MIME detection instead of trusting the extension makes the script more reliable when dealing with mixed archive types.

## Solver Script

This is the script used to peel the layers:

```bash
#!/usr/bin/env bash
set -euo pipefail

src="${1:-layer_100.zip}"

if [[ ! -f "$src" ]]; then
  echo "Missing input: $src" >&2
  exit 1
fi

tmp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

cp "$src" "$tmp_dir/"
target="$tmp_dir/$(basename "$src")"

while [[ -n "$target" ]]; do
  mime="$(file -b --mime-type "$target")"
  name="$(basename "$target")"

  case "$mime" in
    application/zip)
      before="$(find "$tmp_dir" -type f | sort)"
      unzip -qq "$target" -d "$tmp_dir"
      rm -f "$target"
      after="$(find "$tmp_dir" -type f | sort)"
      target="$(comm -13 <(printf '%s\n' "$before") <(printf '%s\n' "$after") | head -n 1)"
      ;;
    application/x-tar)
      before="$(find "$tmp_dir" -type f | sort)"
      tar -xf "$target" -C "$tmp_dir"
      rm -f "$target"
      after="$(find "$tmp_dir" -type f | sort)"
      target="$(comm -13 <(printf '%s\n' "$before") <(printf '%s\n' "$after") | head -n 1)"
      ;;
    application/gzip)
      gunzip -f "$target"
      target="${target%.gz}"
      ;;
    application/x-bzip2)
      bunzip2 -f "$target"
      target="${target%.bz2}"
      ;;
    application/x-xz)
      unxz -f "$target"
      target="${target%.xz}"
      ;;
    text/plain)
      cat "$target"
      exit 0
      ;;
    *)
      echo "Stopped at $name ($mime)" >&2
      file -b "$target" >&2
      exit 1
      ;;
  esac
done

echo "No flag found" >&2
exit 1
```

I saved it as:

```text
solve_onion.sh
```

## Running the Solver

From the challenge directory, I ran:

```powershell
wsl --cd "/mnt/d/CRYPTONITE/The Onion" bash solve_onion.sh
```

That produced the final plain-text payload:

```text
Q29uZ28gaGVyZSBpcyB5b3VyIGZsYWc6IFRBQ0hZT057MV93MG5kM3Jfd2gwc19iM2hpbmRfdGgzX200c2tfM2hmODRoZnJ9
```

That string is clearly Base64.

## Decoding the Final Payload

To decode it, I used:

```powershell
wsl bash -lc "printf '%s' 'Q29uZ28gaGVyZSBpcyB5b3VyIGZsYWc6IFRBQ0hZT057MV93MG5kM3Jfd2gwc19iM2hpbmRfdGgzX200c2tfM2hmODRoZnJ9' | base64 -d"
```

Decoded output:

```text
Congo here is your flag: TACHYON{1_w0nd3r_wh0s_b3hind_th3_m4sk_3hf84hfr}
```

## Flag

```text
TACHYON{1_w0nd3r_wh0s_b3hind_th3_m4sk_3hf84hfr}
```

## Takeaways

- The clue directly pointed to layered extraction.
- `wsl` was the cleanest way to handle mixed archive formats.
- Automating the peel was faster and safer than manually unpacking dozens of layers.
- The archive chain did not end at the flag itself; the last layer contained a Base64-encoded message, so one final decoding step was required.

## Files Created During Solving

- `solve_onion.sh` - helper script used to unpack the nested layers
- `WRITEUP.md` - this write-up

