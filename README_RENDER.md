# Render Deployment Guide

For the complete end-to-end setup (local + Render + Railway), use:
- `README.md`

Quick Render checklist:
1. Push repo to GitHub.
2. Render -> `New +` -> `Blueprint`.
3. Select repo and deploy.
4. Add env var: `OPENAI_API_KEY`.
5. Open `https://<your-render-service>.onrender.com/`.

Note: files in `UPLOAD_DIR` are ephemeral on free plans.
