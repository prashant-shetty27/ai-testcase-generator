# AI Testcase Generator

FastAPI app that generates downloadable `.xlsx` test cases from a requirement prompt.

## 1) Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your_api_key_here"
python main.py
```

Open: `http://localhost:8000/`

## 2) Easiest public hosting (Render)

### Step A: Push this repo to GitHub

```bash
git add .
git commit -m "Prepare deployment"
git push
```

### Step B: Deploy on Render (Blueprint)
1. Go to Render dashboard.
2. Click `New +` -> `Blueprint`.
3. Select your GitHub repo.
4. Render reads `render.yaml` and creates the web service.

### Step C: Add environment variable
In Render service settings, set:
- `OPENAI_API_KEY` = your key

### Step D: Open your public URL
- `https://<your-service-name>.onrender.com/`

## 3) Railway alternative (if you prefer Railway)

1. Push repo to GitHub.
2. In Railway: `New Project` -> `Deploy from GitHub repo`.
3. Add variable `OPENAI_API_KEY`.
4. Deploy (it uses `Dockerfile` / `railway.toml`).

### Auto-update Railway on every push (GitHub Actions)

This repo includes: `.github/workflows/railway-auto-deploy.yml`

It deploys to Railway automatically on every push to `main`.

Add these GitHub repository secrets:
- `RAILWAY_TOKEN` (Railway API token)
- `RAILWAY_SERVICE_ID` (target Railway service id)
- `RAILWAY_ENVIRONMENT_ID` (optional; use when you want a specific environment)

GitHub path:
- `Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

## 4) Important production note (file storage)

Generated files are written to `UPLOAD_DIR`.

- Default on cloud is `/tmp/uploads` (ephemeral).
- Files may be lost after restart/redeploy.

For persistent downloads in production, store generated files in object storage (S3/R2/GCS) and return those links.

## 5) Required environment variables

- `OPENAI_API_KEY` (required)
- `UPLOAD_DIR` (optional, default: `./uploads` locally or `/tmp/uploads` in Render config)
- `AI_MAX_TOKENS` (optional, default: `7000`; increase if you want more generated cases per run)

## 6) Run History Logs

The app now keeps generation run logs in JSON.

- Default file: `logs/run_logs.json`
- Latest run API: `GET /runs/latest`
- Recent runs API: `GET /runs?limit=20`

Optional env vars:
- `RUN_LOG_DIR` (default: `./logs`)
- `RUN_LOG_FILE` (default: `./logs/run_logs.json`)
- `RUN_LOG_MAX_ENTRIES` (default: `300`)
- `RUN_LOG_TITLE_LIMIT` (default: `100`)

## 7) Slack Login (SSO)

Slack OpenID Connect auth is now supported.

Required env vars:
- `SESSION_SECRET` (required in production)
- `SLACK_CLIENT_ID`
- `SLACK_CLIENT_SECRET`
- `SLACK_REDIRECT_URI` (optional; auto-derived from callback URL if not set)

Optional access restrictions:
- `SLACK_ALLOWED_TEAM_ID` (allow only one Slack workspace)
- `SLACK_ALLOWED_EMAIL_DOMAIN` (allow only users from this email domain)

Auth endpoints:
- `GET /auth/slack/login`
- `GET /auth/slack/callback`
- `GET /auth/logout`

Protected endpoints now require login:
- `/generate-tests`
- `/generate-form`
- `/generate-simple`
- `/upload-testcases`
- `/download/{filename}`
- `/runs`
- `/runs/latest`
