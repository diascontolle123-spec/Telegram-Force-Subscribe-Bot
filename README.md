# Telegram Force Subscribe Bot

Bot Telegram Python dengan akses `/getkey` yang hanya dibuka setelah pengguna
join channel `@yazz8ballpool`.

## Fitur

- Memeriksa status join dengan `getChatMember`.
- Menampilkan tombol URL ke channel dan tombol `Cek Status` jika belum join.
- Mengunci semua perintah dan tombol menu sebelum join.
- Menampilkan Reply Keyboard dengan Get Key, Order VIP, Link APK MOD, dan Tutorial
  setelah membership terverifikasi.
- Menyediakan `/getkey`, `/listharga`, `/ordervip`, `/apkninja`,
  `/linkapkmod`, dan `/tutorial`.
- Menyimpan user ID unik yang menjalankan `/start` di SQLite.
- Menyediakan `/stats` khusus untuk Telegram Admin ID yang dikonfigurasi.
- Memberikan masa aktif key 24 jam per user sejak pertama kali `/getkey`
  berhasil digunakan, lalu memperbarui expiry setelah masa aktif habis.
- Token bot tidak disimpan di source code.

## Konfigurasi

Atur dua environment variable berikut:

- `TELEGRAM_BOT_TOKEN` — Secret yang sudah disediakan di workspace.
- `GETKEY_VALUE` — key yang akan dikirim oleh `/getkey`.
- `ADMIN_TELEGRAM_ID` — ID numerik Telegram admin yang boleh memakai `/stats`.
- `VIP_PRICE_LIST` — daftar harga VIP yang dikirim oleh `/ordervip`, bisa berisi
  beberapa baris. Default-nya meminta pengguna menghubungi admin.
- `USERS_DB_PATH` — lokasi database SQLite user, default `data/users.db`.
- `BOT_TIMEZONE` — timezone untuk menampilkan expiry, default `Asia/Jakarta`.

Opsional:

- `CHANNEL_USERNAME` — default `@yazz8ballpool`.
- `CHANNEL_URL` — default `https://t.me/yazz8ballpool`.
- `LOG_LEVEL` — default `INFO`.

Bot harus menjadi administrator di channel agar Telegram mengizinkan
pemeriksaan status anggota.

## Menjalankan

```bash
python main.py
```

Atau gunakan workflow **Telegram Force Subscribe Bot** di Replit.