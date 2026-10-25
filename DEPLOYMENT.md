# Deploy the frontend on Vercel

The complete project runs locally with `py run.py`. Public hosting needs a reachable API and hosted MySQL/MongoDB; Vercel cannot use the databases on your laptop. Do not run the Windows launcher or download MongoDB inside a Vercel build.

## Frontend project settings

Import `saivedant09-gif/Food_Bridge`, choose branch `main`, and configure:

| Setting | Value |
| --- | --- |
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Node.js | 22.x or 24.x |

`frontend/vercel.json` supplies the build/output settings. Navigation uses URL hashes, so no SPA rewrite is needed.

Add `VITE_API_BASE_URL` in the Vercel project's environment variables. Its value must be the HTTPS URL of the deployed FastAPI backend, without a trailing slash. Do not use localhost or 127.0.0.1. Apply the variable to the deployment environments you use, then redeploy after changing it; Vite embeds it at build time.

Without a hosted API, the frontend can render but database pages and submissions cannot work publicly. A successful Vercel frontend build alone does not mean the full system is online.

## Backend hosting

The API remains in `main.py`. A Python host can install `requirements.txt` and start:

```sh
python -m uvicorn main:app --host 0.0.0.0 --port $PORT
```

Vercel also supports a separate FastAPI project from this same repository with root directory `.` and its FastAPI preset. Use a separate Vercel project from the frontend. Configure hosted databases in either case; the local `.env`, MySQL Windows service and `.local/mongodb` are not deployed. The local Windows launcher is not the cloud entry point.

Set these backend-only environment variables through the host's secret settings:

- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
- `MONGO_URI` (hosted URI, including authentication/TLS options supplied by the provider)
- `MONGO_DATABASE`
- `CORS_ORIGINS` (the exact HTTPS frontend domain; comma-separated if multiple origins are needed)

Use the database provider's TLS requirements and network access controls. Import `database/food_bridge.sql` only into a new database: it contains DROP TABLE statements. Import `database/food_reviews.json` into `food_bridge_mongo.food_reviews` as Extended JSON without replacing existing records. Never expose database passwords through VITE_ variables.

The existing API uses demo role selection and has no login/ownership authorization. Keep a demo deployment protected; implementing real account access is required before accepting public users or real donations.

## Verify after hosting

1. Check the backend `/health` response reports both databases connected.
2. Set `VITE_API_BASE_URL` to that API's HTTPS origin and redeploy the frontend.
3. Add the final frontend origin to backend `CORS_ORIGINS`.
4. Verify food, users, request history and reviews load, then test a complete donation workflow using development data.

Official references: [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite), [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [Vite environment variables](https://vite.dev/guide/env-and-mode).
