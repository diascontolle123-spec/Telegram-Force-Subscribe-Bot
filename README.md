# Telegram Force Subscribe Bot

Bot Telegram Python dengan akses `/getkey` yang hanya dibuka setelah pengguna
join channel `@yazz8ballpool`.

## Fitur

- Memeriksa status join dengan `getChatMember`.
- Menampilkan tombol URL ke channel dan tombol `Cek Status` jika belum join.
- Mengunci semua perintah dan tombol menu sebelum join.
- Menampilkan Reply Keyboard dengan Get Key, Order VIP, Link APK MOD, dan Tutorial
  setelah membership terverifikasi.
- Menyediakan `/getkey`, `/ordervip`, `/apkninja`, `/linkapkmod`, dan `/tutorial`.
- Token bot tidak disimpan di source code.

## Konfigurasi

Atur dua environment variable berikut:

- `TELEGRAM_BOT_TOKEN` — Secret yang sudah disediakan di workspace.
- `GETKEY_VALUE` — key yang akan dikirim oleh `/getkey`.
- `VIP_PRICE_LIST` — daftar harga VIP yang dikirim oleh `/ordervip`, bisa berisi
  beberapa baris. Default-nya meminta pengguna menghubungi admin.

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