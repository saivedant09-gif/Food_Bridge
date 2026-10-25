# Food Bridge

A complete local food-donation project: React + Vite frontend, existing FastAPI backend, MySQL for donations and MongoDB for reviews.

For public hosting, see [DEPLOYMENT.md](DEPLOYMENT.md). In Vercel, set the frontend project's Root Directory to `frontend` and provide a hosted API URL through `VITE_API_BASE_URL`. Local databases are not deployed with the frontend.

## Run it on this laptop

**Double-click `START_FOOD_BRIDGE.bat` in the project folder.**

Or open PowerShell in this folder and run:

```powershell
py run.py
```

Open **http://127.0.0.1:5173**. The launcher opens it automatically unless you use `py run.py --no-browser`.

Keep the terminal open while using the project. Press Ctrl+C to stop the processes started by the launcher. The existing MySQL80 Windows service is managed by Windows and starts automatically.

The launcher checks dependencies, starts the project-local MongoDB if needed, checks/initializes data without overwriting existing tables, starts the API on port 8000 and the frontend on port 5173, and waits for readiness. Healthy existing project servers are reused. It does not kill unrelated programs to clear ports.

- Website: http://127.0.0.1:5173
- API documentation: http://127.0.0.1:8000/docs
- Database readiness: http://127.0.0.1:8000/health
- Logs: `.local/api.log`, `.local/frontend.log`, `.local/mongodb.log`

**This laptop is configured.** MySQL and MongoDB are connected; no further credentials or database installation are needed here. The local password is in the ignored `.env`; do not commit or share that file.

## Use the website

1. **Share food:** choose a donor, enter food/quantity/unit, and set a future pickup deadline.
2. **Find food:** browse/search current donations and click Request food.
3. **Requests / NGO view:** choose an NGO and quantity, then send the request.
4. Switch **View as** to **Donor**. Use the request table to approve or reject it.
5. Switch back to **NGO**, choose Record collection, and submit the actual quantity.
6. **Reviews:** select the food and NGO, rate it, and submit feedback. Filter by food ID if needed.

All choices and records come from the real API. Dashboard counts and request statuses refresh after writes. Forms show loading, validation, success and error states. Navigation and tables support mobile screens.

The imported teammate dataset includes 6 users (3 donors, 3 NGOs), food, requests, collections and two reviews. Its original food deadlines were October 18-19, 2026. Those historical listings are visible by unchecking Available only. Local verification added clearly labelled test records and a fresh local demo donation using the real APIs. These are development/demo records, not real-world donation claims.

## Backend behavior and integration

The original POST/PUT routes remain in use. Additive read routes provide the data needed by the UI:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | / | API status |
| GET | /health | MySQL and MongoDB readiness; 503 if unavailable |
| GET | /users?role=DONOR or NGO | Select existing users; private contact fields excluded |
| GET | /food | Food listings, donor and pickup details |
| POST | /food | Publish food |
| GET | /requests | Joined request/collection history; optional donor_id or ngo_id filters |
| POST | /requests | Create an NGO request |
| PUT | /requests/{request_id}/approve | Reserve the requested stock |
| PUT | /requests/{request_id}/reject | Reject a pending request |
| POST | /requests/{request_id}/collect | Record collection and complete the request |
| GET | /reviews | Reviews from MongoDB |
| GET | /reviews/{food_id} | Reviews for one food listing |
| POST | /reviews | Submit a review |

Expired food cannot be requested or approved. Quantities match MySQL's two-decimal precision. Approval locks rows and reserves stock. A partial collection completes that request and returns its uncollected reserved quantity to availability, within the same transaction. A fully collected listing becomes COMPLETED when no reserved stock remains. Duplicate approvals/collections and excessive quantities are rejected.

The existing backend is a local college-project/demo API without authentication or ownership enforcement. View as changes the workspace; it is not sign-in. No social-login or password-recovery flow is presented. Real account authentication would be separate backend work before public hosting. Both development servers and the bundled MongoDB bind to localhost.

## Configuration and persistence

`.env` contains server-only configuration:

| Variable | Default / purpose |
| --- | --- |
| MYSQL_HOST | 127.0.0.1 |
| MYSQL_PORT | 3306 |
| MYSQL_USER | Local MySQL user |
| MYSQL_PASSWORD | Local password, never exposed to the frontend |
| MYSQL_DATABASE | food_bridge |
| MONGO_URI | mongodb://127.0.0.1:27017 |
| MONGO_DATABASE | food_bridge_mongo |
| CORS_ORIGINS | http://127.0.0.1:5173,http://localhost:5173 |

The frontend defaults to `http://127.0.0.1:8000`. To use another backend, set `VITE_API_BASE_URL` in `frontend/.env` and restart Vite. Only the public API URL belongs in VITE_ variables.

MySQL data stays in the existing MySQL service. MongoDB data persists under `.local/mongodb/`. MongoDB 8.0.34 is downloaded from [MongoDB's official distribution](https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-8.0.34.zip), verified against the official SHA-256, and extracted under `.tools/mongodb/`. These folders, logs, credentials, node_modules, build output and virtual environments are ignored by Git. Do not delete `.local/mongodb/` if you want to preserve reviews.

On another Windows laptop, install Python 3.11+ and Node.js 20.19+ or 22.12+ and MySQL 8.0+. Create `.env` from `.env.example` and set that laptop's MySQL credentials. Run `py run.py`; dependencies and MongoDB are installed as needed. First-time MongoDB download is approximately 800 MB. `scripts/setup_data.py` imports the teammate SQL only when the target database does not exist. An existing database is checked, never reset; existing review documents are preserved. The supplied SQL export contains DROP TABLE commands, so do not manually import it over existing data.

## Verified checks

```powershell
# Isolated backend tests (no database writes)
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v

# Live API/database connectivity (project must be running)
.\.venv\Scripts\python.exe -B scripts/verify_local.py

# Full live workflow verification; intentionally adds labelled local test/demo records
.\.venv\Scripts\python.exe -B scripts/verify_local.py --write-demo

# Frontend API tests and production build
cd frontend
npm test
npm run build
```

Verified locally on October 25, 2026:

- Launcher starts MongoDB, API and frontend, with both databases ready.
- 12 isolated backend tests pass and 5 frontend API tests pass.
- Vite production build passes.
- Live API test covers publish, request, approve, reject, partial stock release, full collection, review persistence/filtering, duplicates, quantity errors and expired food.
- Real Chromium browser test covers publishing, requesting, donor approval, partial collection, review submission and review filtering, all against the real backend/databases.
- All five pages render at 390px mobile width without page overflow; no browser JavaScript exceptions.

The installed FastAPI/Starlette TestClient currently emits an upstream httpx deprecation warning; tests pass. There were no pre-existing lint or TypeScript scripts.

For separate development terminals, the original commands remain available:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

```powershell
cd frontend
npm run dev
```

Use the launcher for normal operation so MongoDB is started too. Public deployment and cloud database setup are separate from the local launcher.
