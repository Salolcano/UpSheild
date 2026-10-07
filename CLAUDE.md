# CLAUDE.md

Guidance for Claude Code in this repo.

## Stack
- Contract: `contracts/upshield.py`, GenLayer Intelligent Contract, v0.3.0 style. Keep the two header lines first.
- App: Vite + React 19 + React Router v7 + TypeScript (strict) + Tailwind v4. Routes in `src/routes.tsx` (loaders fetch page data), pages in `src/pages`, providers and flows in `src/components`, GenLayer client in `src/lib/genlayer.ts`.
- Network: Studio Next, RPC https://studio-next.genlayer.com/api, chain ID 61997.
- SDK: `genlayer-js@2.0.0-rc.1` and `@genlayer/transaction-kit@0.1.0-rc.2` (prerelease).

## Commands
- `npm ci` then `npm run dev` / `npm run build` / `npm run lint` / `npm test`
- `npm run e2e` runs an on-chain fund -> quote -> buy (needs PRIVATE_KEY and VITE_UPSHIELD_CONTRACT).

## Rules
- Only contract arithmetic may move money, never model text.
- Timing and ownership rules live in the contract. Current time comes only from `_now()` (transaction timestamp). Coverage times are canonical UTC `YYYY-MM-DDTHH:MM:SSZ`; never send milliseconds.
- Wei amounts exceed JS safe integers: use BigInt, and read exact numbers from raw JSON (see `bigField` in `src/lib/format.ts`).
- Config comes from `.env` (copy `.env.example`). Never commit `.env`.
- Do not describe hosting steps in README.md.
