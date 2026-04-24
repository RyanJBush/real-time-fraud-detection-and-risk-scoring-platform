# Meridian AI Frontend

React + Vite + TypeScript analyst console for Meridian AI fraud platform.

## Scripts
- `npm run dev` - start local dev server
- `npm run lint` - lint JavaScript/JSX files
- `npm run typecheck` - run TypeScript checks
- `npm run build` - production build
- `npm run preview` - preview production build

## Environment
Use `.env.example`:
```bash
cp .env.example .env
```

Default API base:
- `VITE_API_BASE=http://localhost:8000/api`

## Key Pages
- Dashboard (KPI + trends)
- Transactions (ingest + score/rescore)
- Transaction Detail (decision + explanation)
- Review Queue (assign + override + history)
- Fraud Lab (scenario simulation + model evaluation + case clustering)
