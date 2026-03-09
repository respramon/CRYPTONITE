# Capture The Flag PDF Forensics Write-up

## Challenge Summary

Sebuah file PDF berjudul `Capture_the_flag.pdf` diberikan. Secara visual, file ini terlihat normal di PDF viewer karena hanya berisi artikel Wikipedia tentang Capture The Flag. Namun deskripsi challenge memberi petunjuk bahwa:

- ada objek PDF yang mengarah ke "destination" tak terduga,
- seorang developer menemukan model LLM lokalnya mulai menghasilkan referensi aneh,
- target akhirnya adalah menemukan flag.

Petunjuk terakhir dari soal adalah: **gunakan WSL**.

## Flag

`TACHYON{h3ll0_4ff1n3_c1ph3r}`

## Environment

Semua analisis dilakukan dari WSL menggunakan utilitas PDF yang tersedia. Tool yang dipakai:

- `mutool`
- `pdfinfo`
- `strings`
- `python3`

## Step 1: Recon File

Pertama, cek isi direktori kerja:

```powershell
Get-ChildItem
```

Hasilnya hanya ada satu file:

```text
Capture_the_flag.pdf
```

Kemudian cek metadata dasar PDF:

```powershell
wsl bash -lc "cd '/mnt/d/CRYPTONITE/Capture The Flag'; file Capture_the_flag.pdf; pdfinfo Capture_the_flag.pdf 2>/dev/null | sed -n '1,40p'"
```

Informasi penting:

- file adalah PDF versi 1.5,
- jumlah halaman: 5,
- judul: `Capture the flag (cybersecurity) - Wikipedia`.

Ini menguatkan bahwa PDF tampak seperti hasil ekspor Wikipedia biasa.

## Step 2: Verify the Visible Content Looks Normal

Untuk memastikan bahwa isi yang terlihat memang wajar, ekstrak teks dari halaman pertama:

```powershell
wsl bash -lc "cd '/mnt/d/CRYPTONITE/Capture The Flag'; mutool draw -F txt -o - Capture_the_flag.pdf 1 2>/dev/null | sed -n '1,220p'"
```

Teks yang keluar adalah artikel Wikipedia normal tentang CTF. Tidak ada flag yang tampak di konten utama.

Artinya, penyisipan kemungkinan berada pada:

- annotation,
- action,
- named destination,
- object stream,
- atau metadata internal PDF lainnya.

## Step 3: Inspect PDF Structure

Lihat trailer, root, dan page tree:

```powershell
wsl bash -lc "cd '/mnt/d/CRYPTONITE/Capture The Flag'; mutool show Capture_the_flag.pdf trailer; echo '---'; mutool show Capture_the_flag.pdf trailer/Root; echo '---'; mutool show Capture_the_flag.pdf pages"
```

Bagian penting yang terlihat:

```text
/Root 2 0 R
/Dests 5 0 R
page 1 = 10 0 R
page 2 = 11 0 R
page 3 = 12 0 R
page 4 = 13 0 R
page 5 = 14 0 R
```

Karena challenge menyebut objek PDF yang mengarah ke tujuan yang tidak semestinya, area paling menarik adalah:

- `/Dests`,
- `/Annots`,
- `/A` (action),
- `/URI`.

## Step 4: Inspect Page Annotations

Halaman pertama (`10 0 obj`) memiliki banyak annotation:

```powershell
wsl bash -lc "cd '/mnt/d/CRYPTONITE/Capture The Flag'; mutool show Capture_the_flag.pdf 10"
```

Bagian penting:

```text
/Annots [ 19 0 R 20 0 R 21 0 R ... 44 0 R 45 0 R ]
```

Untuk melihat semua annotation dan action yang mereka panggil:

```powershell
wsl bash -lc "cd '/mnt/d/CRYPTONITE/Capture The Flag'; mutool show Capture_the_flag.pdf pages/*/Annots/*/A | sed -n '1,320p'"
```

Sebagian besar hasilnya normal, misalnya link ke:

- `en.wikipedia.org`
- `sans.org`
- `doi.org`
- `ctftime.org`
- sumber referensi lain yang relevan

Namun di antara semua URI itu terdapat satu target yang aneh:

```text
422 0 obj
<<
  /Type /Action
  /S /URI
  /URI (https://gbhwvro{w3ii0_4qq1o3_h1uw3a})
>>
endobj
```

String ini jelas bukan URL normal, dan formatnya sangat mirip flag yang masih terenkripsi.

## Step 5: Locate the Exact Hidden PDF Object

Objek action `422 0 obj` dipanggil oleh annotation `45 0 obj`. Verifikasi langsung:

```powershell
wsl bash -lc "cd '/mnt/d/CRYPTONITE/Capture The Flag'; mutool show Capture_the_flag.pdf 45 422 423 | sed -n '1,120p'"
```

Output:

```text
45 0 obj
<<
  /Type /Annot
  /Subtype /Link
  /A 422 0 R
  /Rect [ 465 575 471 579 ]
  /BS 423 0 R
>>
endobj

422 0 obj
<<
  /Type /Action
  /S /URI
  /URI (https://gbhwvro{w3ii0_4qq1o3_h1uw3a})
>>
endobj

423 0 obj
<<
  /W 0
>>
endobj
```

Interpretasi:

- `45 0 obj` adalah hidden link annotation.
- `Rect [ 465 575 471 579 ]` berarti area kliknya sangat kecil.
- Lebarnya hanya `6` dan tingginya `4`, jadi luasnya `24`.
- `423 0 obj` berisi `/W 0`, artinya border link diset nol, sehingga annotation tidak terlihat.

Ini menjelaskan kenapa PDF viewer tampak normal, tetapi parser atau pipeline training data yang membaca objek PDF mentah tetap bisa menangkap URI tersebut.

## Step 6: Why This Breaks an LLM Pipeline

Challenge statement menyebut model lokal mulai menghasilkan referensi halusinatif. Itu masuk akal karena:

- PDF viewer hanya merender konten visual,
- sedangkan pipeline ekstraksi data untuk LLM sering memproses objek PDF secara lebih mentah,
- termasuk annotation, action, URI, dan struktur internal lainnya.

Akibatnya, model bisa melihat string tersembunyi yang tidak tampak oleh manusia saat membaca PDF secara biasa.

## Step 7: Extract the Candidate Flag

Dari objek `422 0 obj`, kandidat flag yang diperoleh adalah:

```text
gbhwvro{w3ii0_4qq1o3_h1uw3a}
```

Tetapi user mengoreksi bahwa format flag seharusnya adalah:

```text
TACHYON{...}
```

Artinya string ini belum final dan masih terenkripsi.

## Step 8: Identify the Cipher

Prefix ciphertext:

```text
gbhwvro
```

harus berubah menjadi:

```text
tachyon
```

Caesar cipher tidak cocok, karena setiap huruf membutuhkan shift berbeda. Salah satu kandidat paling wajar berikutnya adalah **affine cipher**.

Model affine cipher:

```text
y = (a*x + b) mod 26
```

dengan:

- `x` = indeks huruf ciphertext,
- `y` = indeks huruf plaintext,
- `a` dan `26` harus relatif prima.

Gunakan dua pasangan huruf pertama:

- `g -> t`
- `b -> a`

Konversi ke indeks alfabet (`a=0`):

- `g = 6`, `t = 19`
- `b = 1`, `a = 0`

Sehingga:

```text
6a + b ≡ 19 (mod 26)
1a + b ≡  0 (mod 26)
```

Kurangkan persamaan kedua dari pertama:

```text
5a ≡ 19 (mod 26)
```

Inverse dari `5 mod 26` adalah `21`, jadi:

```text
a ≡ 19 * 21 ≡ 399 ≡ 9 (mod 26)
```

Substitusi ke persamaan kedua:

```text
9 + b ≡ 0 (mod 26)
b ≡ 17 (mod 26)
```

Jadi fungsi dekripsinya adalah:

```text
y = (9x + 17) mod 26
```

## Step 9: Decode the Full String

Verifikasi cepat dengan Python di WSL:

```powershell
wsl bash -lc "python3 - <<'PY'
from string import ascii_lowercase as lc
ct='gbhwvro{w3ii0_4qq1o3_h1uw3a}'
pt=''.join(lc[(9*lc.index(ch)+17)%26] if ch in lc else ch for ch in ct)
print(pt)
PY"
```

Output:

```text
tachyon{h3ll0_4ff1n3_c1ph3r}
```

Karena format resmi flag menggunakan prefix uppercase, flag akhirnya adalah:

```text
TACHYON{h3ll0_4ff1n3_c1ph3r}
```

## Full Solve Script

Berikut versi ringkas solve script yang bisa dijalankan langsung di WSL:

```python
from string import ascii_lowercase as lc

ciphertext = "gbhwvro{w3ii0_4qq1o3_h1uw3a}"

plaintext = "".join(
    lc[(9 * lc.index(ch) + 17) % 26] if ch in lc else ch
    for ch in ciphertext
)

print(plaintext)
print(plaintext.replace("tachyon{", "TACHYON{", 1))
```

## Final Answer

`TACHYON{h3ll0_4ff1n3_c1ph3r}`

## Key Takeaways

1. PDF yang tampak normal bisa menyimpan data tersembunyi pada annotation/action objects.
2. Hidden link annotation dengan area sangat kecil dan border nol dapat lolos dari pembacaan visual manusia.
3. Pipeline ekstraksi untuk LLM dapat memproses objek yang tidak dirender, sehingga memunculkan data tersembunyi ke model.
4. Setelah string tersembunyi ditemukan, sisanya adalah decoding affine cipher menggunakan known plaintext dari format flag.
