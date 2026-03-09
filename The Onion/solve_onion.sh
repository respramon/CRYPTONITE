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
