# Telegram Force Subscribe Bot

Bot Telegram Python dengan akses `/getkey` yang hanya dibuka setelah pengguna
join channel `@yazz8ballpool`.

## Fitur

- Memeriksa status join dengan `getChatMember`.
- Menampilkan tombol URL ke channel dan tombol `Cek Status` jika belum join.
- Mengunci `/getkey`, `/help`, perintah lain, dan pesan biasa sebelum join.
- Mengirim key hanya setelah membership terverifikasi.
- Token bot tidak disimpan di source code.

## Konfigurasi

Atur dua environment variable berikut:

- `TELEGRAM_BOT_TOKEN` — Secret yang sudah disediakan di workspace.
- `GETKEY_VALUE` — key yang akan dikirim oleh `/getkey`.

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