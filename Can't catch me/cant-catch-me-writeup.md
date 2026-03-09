# Can't catch me - OSINT Write-up

## Ringkasan

Dari satu file gambar yang ditinggalkan attacker, jejak utama ternyata bukan berasal dari metadata EXIF, melainkan dari string yang tertanam di dalam file JPEG. String itu mengarah ke sebuah repository GitHub, lalu riwayat commit di repo tersebut mengarah ke akun Reddit, dan postingan Reddit berisi flag yang di-encode dengan Base64.

Hasil akhir:

- Person of interest: `SirLancelot-13` / `SirLancelotDuLac`
- Identitas yang paling mungkin: `Pragyan Srivastava` (inferensi kuat dari metadata commit publik)
- Afiliasi publik: mahasiswa CSE di IIT Tirupati
- Flag: `TACHYON{S0c14l_m3d14_tr4il5_4r3_sc4ry_2fw3g4}`

## Artefak Awal

File yang diberikan:

- `WhatsApp_Image_2026-02-27_at_14.24.21.jpeg`

Secara visual, gambar hanya menampilkan area outdoor saat senja: jalan landai/ramp, pepohonan, lampu taman, dan bangunan. Tidak ada petunjuk identitas yang jelas dari tampilan visual saja.

Resolusi gambar:

- `1200 x 1600`

## Langkah 1 - Enumerasi String dari JPEG

Karena gambar WhatsApp sering kehilangan EXIF, langkah pertama adalah memeriksa string ASCII yang masih tertanam di file JPEG.

Saat string diekstrak dari file, muncul petunjuk yang sangat penting:

```text
JFIF
Photoshop 3.0
https://github.com/SirLancelot-13/sample-repo/
```

Ini adalah pivot pertama yang mengubah challenge dari analisis gambar biasa menjadi OSINT berbasis akun online.

## Langkah 2 - Investigasi Repository GitHub

URL di atas mengarah ke repository berikut:

- Repository: `https://github.com/SirLancelot-13/sample-repo`
- Owner: `https://github.com/SirLancelot-13`

Beberapa hal yang bisa dikumpulkan dari profil dan API GitHub:

- Username GitHub: `SirLancelot-13`
- Display name GitHub: `SirLancelotDuLac`
- Bio profil: `Just a guy trying to tinker with stuff...`
- Profil/README pengguna menyatakan bahwa dia adalah mahasiswa S1 Computer Science Engineering di IIT Tirupati.

Ini memberi kita identitas operasional yang cukup jelas: akun GitHub publik milik seseorang yang mengasosiasikan dirinya dengan IIT Tirupati.

## Langkah 3 - Menambang Riwayat Commit

Berikutnya, riwayat commit repo `sample-repo` diperiksa.

Commit yang relevan:

- `Initial Commit`
- `Add initial README with project description`
- `Cleaned sum stuff up`
- merge commit setelahnya

Commit paling penting adalah:

- `e628ee7e603b6f0815062971713fe95df4307720`
- URL: `https://github.com/SirLancelot-13/sample-repo/commit/e628ee7e603b6f0815062971713fe95df4307720`

Diff commit ini menunjukkan bahwa sebuah komentar dihapus dari file `guess_the_number.py`:

```python
#Note: I might not be available for a few days so jus leave me a message at my reddit account: u/11t_tpt_d4_g04t
```

Ini adalah pivot kedua: GitHub -> Reddit.

## Langkah 4 - Menentukan Identitas Person of Interest

Dari API commit GitHub, metadata author publik menunjukkan nama akun penulis dan sebuah alamat email dengan pola nama yang sangat spesifik:

- author name: `SirLancelot13` / `SirLancelotDuLac`
- email commit mengandung string `pragyansrivastava13`

Inferensi yang paling kuat dari metadata ini adalah bahwa nama asli orang tersebut kemungkinan besar:

- `Pragyan Srivastava`

Catatan penting:

- Ini adalah inferensi kuat dari metadata commit publik, bukan verifikasi identitas resmi.
- Yang dapat dipastikan langsung dari sumber publik adalah alias GitHub `SirLancelot-13` / `SirLancelotDuLac`.
- Yang juga dapat dipastikan dari profil publik adalah afiliasi self-claimed sebagai mahasiswa CSE di IIT Tirupati.

Karena challenge meminta "find the person", jawaban yang paling aman dan tepat adalah:

- Person of interest: `SirLancelot-13` alias `SirLancelotDuLac`
- Likely real name: `Pragyan Srivastava`

## Langkah 5 - Pivot ke Akun Reddit

Dari komentar yang dihapus, akun Reddit yang dituju adalah:

- `u/11t_tpt_d4_g04t`
- URL: `https://www.reddit.com/user/11t_tpt_d4_g04t/`

Pencarian web terhadap username ini memperlihatkan sebuah posting dari akun tersebut dengan isi encoded string:

```text
VEFDSFlPTntTMGMxNGxfbTNkMTRfdHI0aWw1XzRyM19zYzRyeV8yZnczZzR9
```

## Langkah 6 - Decode Flag

String di atas terlihat seperti Base64. Setelah di-decode, hasilnya adalah:

```text
TACHYON{S0c14l_m3d14_tr4il5_4r3_sc4ry_2fw3g4}
```

Itulah flag challenge ini.

## Kenapa Jalur Ini Benar

Rantai petunjuknya konsisten dan natural:

1. Gambar mengandung URL GitHub yang tertanam.
2. Repo GitHub tersebut memang aktif pada tanggal yang konsisten dengan nama file gambar.
3. Riwayat commit repo memuat komentar yang dihapus berisi akun Reddit.
4. Akun Reddit tersebut memposting string Base64.
5. Base64 tersebut menghasilkan string berformat flag CTF.

Tidak ada lompatan logika yang besar di antara tahap-tahap ini; setiap pivot berasal dari artefak publik yang memang terhubung satu sama lain.

## Reproduksi Singkat

Contoh langkah yang bisa dipakai untuk mereproduksi solve:

### 1. Ekstrak string dari JPEG

```powershell
$bytes = [System.IO.File]::ReadAllBytes('WhatsApp_Image_2026-02-27_at_14.24.21.jpeg')
$text = [System.Text.Encoding]::ASCII.GetString($bytes)
[regex]::Matches($text,'[ -~]{4,}') | ForEach-Object { $_.Value }
```

Output penting yang dicari:

```text
https://github.com/SirLancelot-13/sample-repo/
```

### 2. Lihat profil GitHub

```text
https://github.com/SirLancelot-13
https://api.github.com/users/SirLancelot-13
```

Data penting:

- login: `SirLancelot-13`
- name: `SirLancelotDuLac`
- bio: `Just a guy trying to tinker with stuff...`

### 3. Ambil riwayat commit repo

```text
https://api.github.com/repos/SirLancelot-13/sample-repo/commits
https://api.github.com/repos/SirLancelot-13/sample-repo/commits/e628ee7e603b6f0815062971713fe95df4307720
```

Data penting:

- commit `Cleaned sum stuff up`
- patch diff menghapus komentar berisi akun Reddit `u/11t_tpt_d4_g04t`

### 4. Kunjungi akun Reddit yang disebut

```text
https://www.reddit.com/user/11t_tpt_d4_g04t/
```

Cari post yang memuat string:

```text
VEFDSFlPTntTMGMxNGxfbTNkMTRfdHI0aWw1XzRyM19zYzRyeV8yZnczZzR9
```

### 5. Decode Base64

```powershell
[Text.Encoding]::UTF8.GetString(
  [Convert]::FromBase64String('VEFDSFlPTntTMGMxNGxfbTNkMTRfdHI0aWw1XzRyM19zYzRyeV8yZnczZzR9')
)
```

Hasil:

```text
TACHYON{S0c14l_m3d14_tr4il5_4r3_sc4ry_2fw3g4}
```

## Final Answer

### Person of Interest

- Alias: `SirLancelot-13`
- Display name: `SirLancelotDuLac`
- Likely real name: `Pragyan Srivastava`
- Public affiliation: mahasiswa CSE di IIT Tirupati

### Flag

```text
TACHYON{S0c14l_m3d14_tr4il5_4r3_sc4ry_2fw3g4}
```

## Referensi

- GitHub profile: `https://github.com/SirLancelot-13`
- GitHub sample repo: `https://github.com/SirLancelot-13/sample-repo`
- Commit yang menghapus petunjuk Reddit: `https://github.com/SirLancelot-13/sample-repo/commit/e628ee7e603b6f0815062971713fe95df4307720`
- Reddit account: `https://www.reddit.com/user/11t_tpt_d4_g04t/`
