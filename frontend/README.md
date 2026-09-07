# VeriTrace console (thin UI)

Operator console for the verification pipeline. The FastAPI backend is the
source of truth; this UI renders run state, candidates, evidence, and chain
status only. See `../docs/RUN_API.md` for the contract.

```bash
npm install
npm run dev      # http://localhost:5173, expects the API at http://localhost:8000
npm test         # vitest
npm run lint     # eslint, must be clean
npm run build    # typecheck + production build
```

Copy `.env.example` to `.env` to point at a non-default API base URL.
