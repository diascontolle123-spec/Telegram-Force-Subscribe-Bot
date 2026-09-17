# Telegram Force Subscribe Bot

Bot Telegram Python yang mengunci akses sampai pengguna join channel dan
memberikan key melalui `/getkey` setelah status keanggotaan terverifikasi.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `python main.py` — run the Telegram bot
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required secrets: `TELEGRAM_BOT_TOKEN`, `GETKEY_VALUE`
- Required env: `ADMIN_TELEGRAM_ID`

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `main.py` — Telegram bot, Force Subscribe checks, callbacks, and `/getkey`
- `data/users.db` — SQLite database for users, stats, and per-user key expiry
- `README.md` — setup and operation notes

## Architecture decisions

- Telegram membership is checked live with `getChatMember` before every protected action.
- The bot uses polling so it runs as a long-lived console workflow without a public webhook.
- Bot token and returned key are stored as Replit Secrets, not committed to source code.

## Product

Users must join `@yazz8ballpool` before they can access the key. Unjoined users
receive a channel link and a status-check button; joined users can use `/getkey`.

## User preferences

The requested channel is `@yazz8ballpool`.

## Gotchas

- The bot must be an administrator in the channel for reliable membership checks.
- `/getkey` requires the `GETKEY_VALUE` Secret to be configured before startup.
- `/stats` requires the numeric `ADMIN_TELEGRAM_ID` environment variable.
- Key expiry is stored per Telegram user and is renewed only after 24 hours have elapsed.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
