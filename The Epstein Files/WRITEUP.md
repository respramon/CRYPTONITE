# The Epstein Files Write-up

## Challenge Summary

We are given a single file:

- `output.pdf`

The prompt implies that something has been hidden in an "extract" of the Epstein files, and that some information may have been "erased from plain view". The correct solve path is PDF forensics: inspect the document structure, identify hidden/orphaned content, recover the concealed ciphertext, and decrypt it to obtain the flag.

Final flag:

```text
TACHYON{PDF_St3g4n0gr4phy_i5_kool_5tau36}
```

## Initial Recon

The workspace initially contained only the PDF:

```powershell
Get-ChildItem -Force
```

The file was:

```text
output.pdf
```

At this point the obvious first step was to inspect the visible text, metadata, and raw PDF structure.

## Visible PDF Content

Rendering or extracting text from the visible pages shows a fake-looking "supplemental records review summary" with redacted names and a few crypto-looking values.

The most important visible value is on page 3:

```text
Password reference string recovered from notebook corresponding AES-128 Key:
3f9c2a7b8d4e1f609a2b3c4d5e6f7081
```

That is a strong clue that AES will be involved later.

Using `mutool` under WSL to dump visible text:

```bash
wsl.exe bash -lc 'cd /mnt/d/CRYPTONITE/The\ Epstein\ Files && mutool draw -F txt output.pdf'
```

This confirms the visible report is ordinary text and contains the AES key above, but nothing that directly looks like the flag.

## Raw PDF Inspection

The next step is to inspect the PDF at the object level.

Useful commands:

```bash
wsl.exe bash -lc 'cd /mnt/d/CRYPTONITE/The\ Epstein\ Files && exiftool output.pdf'
wsl.exe bash -lc 'cd /mnt/d/CRYPTONITE/The\ Epstein\ Files && mutool show output.pdf trailer'
wsl.exe bash -lc 'cd /mnt/d/CRYPTONITE/The\ Epstein\ Files && strings -n 6 output.pdf | sed -n "1,260p"'
```

Important findings:

### 1. The PDF is malformed on purpose

`mutool` reports:

```text
format error: cannot recognize xref format
warning: trying to repair broken xref
warning: repairing PDF document
```

This strongly suggests the file was intentionally manipulated.

### 2. There is a hidden IV in the PDF header comment

Very early in the file, before the main objects, there is this line:

```text
%aes-iv key:a1b2c3d4e5f60718293a4b5c6d7e8f90
```

That is not standard PDF content. It is a deliberate clue. Despite the label saying `aes-iv key`, the value is 16 bytes long and is used as the AES IV.

So we now have:

- AES key from visible page text:
  - `3f9c2a7b8d4e1f609a2b3c4d5e6f7081`
- AES IV from the PDF header comment:
  - `a1b2c3d4e5f60718293a4b5c6d7e8f90`

### 3. There is an orphaned extra page object

Raw `strings` output reveals an unusual object relationship:

```text
2 0 obj
<< ... /Name << /Extra << /Name [ (Extra) 6 0 R ] >> >> ... >>
```

And object `6` is:

```text
6 0 obj
<< /Contents 10 0 R ... /Type /Page >>
```

But the actual page tree is:

```text
4 0 obj
<< /Count 3 /Kids [ 7 0 R 8 0 R 9 0 R ] /Type /Pages >>
```

So the visible PDF has three normal pages: `7`, `8`, and `9`.

Object `6` is also a page, but it is not in the page tree. It is an orphan page: present in the file, but not displayed by normal viewers.

That is the core hiding trick.

## Why Object 6 Matters

Object `6` references content stream `10` and has different resources from the visible pages:

```text
/GS47 13 0 R
/GS48 14 0 R
/XObject << /Image38 17 0 R /Image40 18 0 R >>
```

The special graphics states are:

```text
13 0 obj
<< /BM /Normal /Type /ExtGState /ca 0 >>

14 0 obj
<< /BM /Normal /CA 0 /Type /ExtGState >>
```

These correspond to zero alpha values, meaning content can exist in the PDF but be fully invisible.

That is exactly the sort of "erased from plain view" behavior suggested by the prompt.

## Extracting the Hidden Page

To inspect the orphan page properly, I rebuilt it into a standalone PDF and rendered it.

### Step 1: Build `orphan6.pdf`

```python
from pypdf import PdfReader, PdfWriter
from pypdf._page import PageObject
from pypdf.generic import IndirectObject, NameObject

reader = PdfReader("output.pdf", strict=False)
obj6 = reader.get_object(IndirectObject(6, 0, reader))

page = PageObject(reader)
page.update(obj6)
try:
    del page[NameObject("/Parent")]
except Exception:
    pass

writer = PdfWriter()
writer.add_page(page)

with open("orphan6.pdf", "wb") as f:
    writer.write(f)
```

### Step 2: Render it

```bash
wsl.exe bash -lc 'cd /mnt/d/CRYPTONITE/The\ Epstein\ Files && mutool draw -o orphan6.png -r 150 orphan6.pdf 1'
```

This reveals that the hidden page is an old book page image with a yellow overlay containing upside-down hexadecimal text.

The hidden page is not part of the visible document flow, so a normal viewer never shows it.

## Recovering the Hidden Hex

After rendering the orphan page, the hidden yellow text can be isolated by cropping around the non-white, yellow-ish pixels.

The crop reveals the full ciphertext:

```text
4fc80625b049f68462f7d02e7
9a8cbc1875ecd11a2b331eacc
c998fc9ffb3647d0adb35e9930
15f4aa88c894c09a9a67
```

Concatenated:

```text
4fc80625b049f68462f7d02e79a8cbc1875ecd11a2b331eaccc998fc9ffb3647d0adb35e993015f4aa88c894c09a9a67
```

This is 96 hex characters, or 48 bytes, which is a valid AES-CBC ciphertext length.

## Cross-Checking the Hidden Stream

The orphan page content stream `10` also contains hidden/invisible text blocks using `/GS47` and `/GS48`.

Decoding that stream shows:

- an orphan page image background
- invisible text blocks
- extra drawn overlay content

The invisible text helped confirm that the hidden payload was hexadecimal, but the fully correct ciphertext is most reliably recovered from the rendered yellow overlay on the orphan page.

That is why the visual extraction matters: the hidden page contains the complete 4-line hex string.

## Decryption

At this point we have:

- Key:
  - `3f9c2a7b8d4e1f609a2b3c4d5e6f7081`
- IV:
  - `a1b2c3d4e5f60718293a4b5c6d7e8f90`
- Ciphertext:
  - `4fc80625b049f68462f7d02e79a8cbc1875ecd11a2b331eaccc998fc9ffb3647d0adb35e993015f4aa88c894c09a9a67`

Decrypt with AES-CBC:

```python
from Crypto.Cipher import AES

key = bytes.fromhex("3f9c2a7b8d4e1f609a2b3c4d5e6f7081")
iv = bytes.fromhex("a1b2c3d4e5f60718293a4b5c6d7e8f90")
ct = bytes.fromhex("4fc80625b049f68462f7d02e79a8cbc1875ecd11a2b331eaccc998fc9ffb3647d0adb35e993015f4aa88c894c09a9a67")

pt = AES.new(key, AES.MODE_CBC, iv=iv).decrypt(ct)
print(pt)
print(pt.hex())
```

Decrypted plaintext:

```text
TACHYON{PDF_St3g4n0gr4phy_i5_kool_5tau36}
```

Hex output of the plaintext:

```text
54414348594f4e7b5044465f53743367346e306772347068795f69355f6b6f6f6c5f3574617533367d07070707070707
```

The trailing `07` bytes are valid PKCS#7 padding, confirming that the AES-CBC decryption is correct and complete.

## Final Flag

```text
TACHYON{PDF_St3g4n0gr4phy_i5_kool_5tau36}
```

## Full Solve Logic

In short, the solve works because the author split the puzzle across multiple PDF layers and conventions:

1. The visible PDF pages contain a decoy report and a visible AES key.
2. The PDF header comment contains the IV.
3. The file has a broken xref table to make casual parsing harder.
4. A hidden orphan page object exists outside the page tree.
5. That orphan page contains the real payload as upside-down yellow hex over a book-page background.
6. Recovering that hex and decrypting it with the visible key and hidden IV yields the flag.

## Minimal Reproduction Commands

If you want the shortest possible reproduction path:

### Inspect page tree and orphan object

```bash
wsl.exe bash -lc 'cd /mnt/d/CRYPTONITE/The\ Epstein\ Files && mutool show output.pdf pages'
wsl.exe bash -lc 'cd /mnt/d/CRYPTONITE/The\ Epstein\ Files && mutool show output.pdf 6'
```

### Inspect raw clues

```bash
wsl.exe bash -lc 'cd /mnt/d/CRYPTONITE/The\ Epstein\ Files && strings -n 6 output.pdf | sed -n "1,260p"'
```

### Extract and render the orphan page

Use the Python snippet above to create `orphan6.pdf`, then:

```bash
wsl.exe bash -lc 'cd /mnt/d/CRYPTONITE/The\ Epstein\ Files && mutool draw -o orphan6.png -r 150 orphan6.pdf 1'
```

### Decrypt

```python
from Crypto.Cipher import AES

key = bytes.fromhex("3f9c2a7b8d4e1f609a2b3c4d5e6f7081")
iv = bytes.fromhex("a1b2c3d4e5f60718293a4b5c6d7e8f90")
ct = bytes.fromhex("4fc80625b049f68462f7d02e79a8cbc1875ecd11a2b331eaccc998fc9ffb3647d0adb35e993015f4aa88c894c09a9a67")

print(AES.new(key, AES.MODE_CBC, iv=iv).decrypt(ct))
```

## Conclusion

This challenge is a good example of PDF steganography and PDF object abuse:

- hidden metadata clues
- orphaned page objects
- malformed xref repair behavior
- invisible drawing states
- visually concealed payloads embedded in non-displayed content

The final recovered flag is:

```text
TACHYON{PDF_St3g4n0gr4phy_i5_kool_5tau36}
```
