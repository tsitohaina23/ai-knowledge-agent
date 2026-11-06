# Frontend: AI Knowledge Agent

React 19, TypeScript, Vite and Tailwind CSS. It talks to the local FastAPI backend (see the root README).

```bash
npm install
npm run dev      # http://localhost:5173 (expects the API on http://localhost:8000)
npm run build    # production build in dist/
npm run lint     # oxlint
```

Copy `.env.example` to `.env` to point to another API URL (`VITE_API_URL`).
To serve the built UI from the API itself, start the backend with `STATIC_DIR=../frontend/dist`.
