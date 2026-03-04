import re
import shutil
import os
import secrets
from pathlib import Path
from datetime import datetime
from time import perf_counter
from urllib.parse import urlencode

import httpx
from fastapi import Form, Request, FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from models.test_request import TestGenerationRequest
from services.test_generation_service import generate_full_test_suite
from run_logger import (
    summarize_tests,
    log_generation_run,
    list_run_logs,
    get_latest_run_log,
)
from excel_exporter import (
    export_to_excel,
    read_existing_testcases,
    normalize_existing_testcases
)

app = FastAPI(title="AI Testcase Generator", version="1.0")

SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-in-production")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").strip().lower() in {"1", "true", "yes", "on"}
SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID", "")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET", "")
SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI", "")
SLACK_ALLOWED_TEAM_ID = os.getenv("SLACK_ALLOWED_TEAM_ID", "")
SLACK_ALLOWED_EMAIL_DOMAIN = os.getenv("SLACK_ALLOWED_EMAIL_DOMAIN", "")

SLACK_OIDC_AUTHORIZE_URL = "https://slack.com/openid/connect/authorize"
SLACK_OIDC_TOKEN_URL = "https://slack.com/api/openid.connect.token"
SLACK_OIDC_USERINFO_URL = "https://slack.com/api/openid.connect.userInfo"

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=SESSION_COOKIE_SECURE,
)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_JIRA_MACRO_RE = re.compile(r"\{[^}]{0,40}\}")           # {*}, {+}, {color:red}, {quote} …
_JIRA_HEADING_RE = re.compile(r"^h[1-6]\.\s*", re.MULTILINE)  # h1. h2. h3. …
_JIRA_UNDERLINE_RE = re.compile(r"\+([^+\n]{1,300}?)\+")      # +underline+ → text
_JIRA_BULLET_RE = re.compile(r"^[ \t]*\*+\s+", re.MULTILINE)  # " * item" bullets

_HTML_ENTITIES = {
    "&amp;": "&", "&lt;": "<", "&gt;": ">",
    "&nbsp;": " ", "&quot;": '"', "&apos;": "'",
}

def _clean_requirement(text: str) -> str:
    """Strip HTML tags, HTML entities, and Jira wiki markup so the AI receives clean plain text."""
    if not text:
        return text
    for entity, char in _HTML_ENTITIES.items():
        text = text.replace(entity, char)
    text = _HTML_TAG_RE.sub("", text)
    text = _JIRA_MACRO_RE.sub("", text)
    text = _JIRA_HEADING_RE.sub("", text)
    text = _JIRA_UNDERLINE_RE.sub(r"\1", text)
    text = _JIRA_BULLET_RE.sub("- ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
UPLOAD_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=BASE_DIR / "web/templates")


def _slack_is_configured() -> bool:
    return bool(SLACK_CLIENT_ID and SLACK_CLIENT_SECRET)


def _resolve_slack_redirect_uri(request: Request) -> str:
    if SLACK_REDIRECT_URI:
        return SLACK_REDIRECT_URI
    return str(request.url_for("auth_slack_callback"))


def _get_current_user(request: Request):
    return request.session.get("user")


def _require_authenticated_user(request: Request):
    user = _get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized. Please login via Slack.")
    return user


def _merge_existing_with_generated(existing_cases: list[dict], generated_tests: dict) -> dict:
    """
    Preserve uploaded cases while appending newly generated unique cases.
    """
    merged: dict = {}

    for case in existing_cases or []:
        if not isinstance(case, dict):
            continue
        category = case.get("category") or "existing_tests"
        merged.setdefault(category, []).append(case)

    for category, cases in (generated_tests or {}).items():
        if not isinstance(cases, list):
            continue
        merged.setdefault(category, []).extend(cases)

    return merged


def _build_run_request_payload(
    requirement: str,
    template: str,
    platforms=None,
    modules=None,
    pages=None,
    test_types=None,
    existing_filename=None,
    output_filename=None,
    update_comment=None,
) -> dict:
    return {
        "requirement": requirement,
        "template": template,
        "platforms": [str(p) for p in (platforms or [])],
        "modules": [str(m) for m in (modules or [])],
        "pages": [str(p) for p in (pages or [])],
        "test_types": [str(t) for t in (test_types or [])],
        "existing_filename": existing_filename,
        "output_filename": output_filename,
        "update_comment": update_comment,
    }


# -------------------------
# GENERATE TESTS
# -------------------------
@app.post("/generate-tests")
def generate(request: TestGenerationRequest, http_request: Request):
    _require_authenticated_user(http_request)
    started_at = perf_counter()
    request.requirement = _clean_requirement(request.requirement)
    run_request_payload = _build_run_request_payload(
        requirement=request.requirement,
        template=request.template,
        platforms=request.platforms,
        modules=request.modules,
        pages=request.pages,
        test_types=request.test_types,
        existing_filename=request.existing_filename,
        output_filename=request.output_filename,
        update_comment=request.update_comment,
    )

    try:
        if not request.requirement:
            raise HTTPException(status_code=400, detail="Requirement cannot be empty")

        # -------- UPDATE FLOW --------
        if request.existing_filename:
            file_path = UPLOAD_DIR / request.existing_filename

            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")

            raw_cases = read_existing_testcases(file_path)
            existing_cases = normalize_existing_testcases(raw_cases)

            generated_tests = generate_full_test_suite(
                request,
                existing_cases=existing_cases,
                update_comment=request.update_comment
            )
            tests = _merge_existing_with_generated(existing_cases, generated_tests)

            export_to_excel(
                tests,
                template_type=request.template,
                output_path=file_path
            )

            response_payload = {
                "message": "Existing testcases updated",
                "download_url": f"/download/{file_path.name}"
            }

            log_generation_run(
                endpoint="/generate-tests",
                status="success",
                request_payload=run_request_payload,
                result_payload={
                    "mode": "update",
                    "file_name": file_path.name,
                    "download_url": response_payload["download_url"],
                    "generated_summary": summarize_tests(generated_tests),
                    "merged_summary": summarize_tests(tests),
                },
                duration_ms=int((perf_counter() - started_at) * 1000),
            )
            return response_payload

        # -------- FRESH FLOW --------
        tests = generate_full_test_suite(request)

        if request.output_filename:
            filename = f"{request.output_filename}.xlsx"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_{request.template}_{timestamp}.xlsx"
        file_path = UPLOAD_DIR / filename

        export_to_excel(
            tests,
            template_type=request.template,
            output_path=file_path
        )

        response_payload = {
            "message": "Generated successfully",
            "download_url": f"/download/{filename}"
        }

        log_generation_run(
            endpoint="/generate-tests",
            status="success",
            request_payload=run_request_payload,
            result_payload={
                "mode": "fresh",
                "file_name": filename,
                "download_url": response_payload["download_url"],
                "generated_summary": summarize_tests(tests),
            },
            duration_ms=int((perf_counter() - started_at) * 1000),
        )
        return response_payload
    except HTTPException as exc:
        log_generation_run(
            endpoint="/generate-tests",
            status="failed",
            request_payload=run_request_payload,
            error=str(exc.detail),
            duration_ms=int((perf_counter() - started_at) * 1000),
        )
        raise
    except Exception as exc:
        log_generation_run(
            endpoint="/generate-tests",
            status="failed",
            request_payload=run_request_payload,
            error=str(exc),
            duration_ms=int((perf_counter() - started_at) * 1000),
        )
        raise


# -------------------------
# UPLOAD EXISTING FILE
# -------------------------
@app.post("/upload-testcases")
async def upload_testcases(request: Request, file: UploadFile = File(...)):
    _require_authenticated_user(request)

    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx allowed")

    file_path = UPLOAD_DIR / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "message": "File uploaded successfully",
        "filename": file.filename
    }


# -------------------------
# DOWNLOAD
# -------------------------
@app.get("/download/{filename}", response_class=FileResponse, responses={404: {"description": "File not found"}, 200: {"content": {"application/octet-stream": {}}}})
def download(filename: str, request: Request):
    _require_authenticated_user(request)

    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = _get_current_user(request)
    if not user:
        response = templates.TemplateResponse(
            "login.html",
            {"request": request, "slack_configured": _slack_is_configured()},
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    response = templates.TemplateResponse("index.html", {"request": request, "user": user})
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/auth/slack/login")
async def auth_slack_login(request: Request):
    if _get_current_user(request):
        return RedirectResponse(url="/", status_code=302)

    if not _slack_is_configured():
        raise HTTPException(
            status_code=500,
            detail="Slack SSO not configured. Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET.",
        )

    state = secrets.token_urlsafe(24)
    request.session["slack_oauth_state"] = state

    params = {
        "response_type": "code",
        "client_id": SLACK_CLIENT_ID,
        "scope": "openid profile email",
        "redirect_uri": _resolve_slack_redirect_uri(request),
        "state": state,
    }
    return RedirectResponse(
        url=f"{SLACK_OIDC_AUTHORIZE_URL}?{urlencode(params)}",
        status_code=302,
    )


@app.get("/auth/slack/callback")
async def auth_slack_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    if error:
        raise HTTPException(status_code=400, detail=f"Slack login failed: {error}")

    expected_state = request.session.pop("slack_oauth_state", None)
    if not code or not state or state != expected_state:
        raise HTTPException(status_code=400, detail="Invalid Slack OAuth state.")

    redirect_uri = _resolve_slack_redirect_uri(request)
    async with httpx.AsyncClient(timeout=20) as client:
        token_response = await client.post(
            SLACK_OIDC_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": SLACK_CLIENT_ID,
                "client_secret": SLACK_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
            },
        )
        token_json = token_response.json()
        if not token_response.is_success or not token_json.get("ok"):
            raise HTTPException(
                status_code=401,
                detail=f"Slack token exchange failed: {token_json.get('error', 'unknown_error')}",
            )

        access_token = token_json.get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="Slack access token missing.")

        userinfo_response = await client.get(
            SLACK_OIDC_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo = userinfo_response.json()
        if not userinfo_response.is_success or not userinfo.get("ok"):
            raise HTTPException(
                status_code=401,
                detail=f"Slack userinfo fetch failed: {userinfo.get('error', 'unknown_error')}",
            )

    team_id = userinfo.get("https://slack.com/team_id") or userinfo.get("team_id")
    email = userinfo.get("email", "")

    if SLACK_ALLOWED_TEAM_ID and team_id != SLACK_ALLOWED_TEAM_ID:
        raise HTTPException(status_code=403, detail="Your Slack workspace is not allowed.")

    if SLACK_ALLOWED_EMAIL_DOMAIN:
        allowed_suffix = f"@{SLACK_ALLOWED_EMAIL_DOMAIN.lower().lstrip('@')}"
        if not email.lower().endswith(allowed_suffix):
            raise HTTPException(status_code=403, detail="Your email domain is not allowed.")

    request.session["user"] = {
        "sub": userinfo.get("sub"),
        "name": userinfo.get("name"),
        "email": email,
        "picture": userinfo.get("picture"),
        "team_id": team_id,
    }
    return RedirectResponse(url="/", status_code=302)


@app.get("/auth/logout")
async def auth_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)


@app.get("/runs")
def get_runs(request: Request, limit: int = 20):
    _require_authenticated_user(request)
    return {"runs": list_run_logs(limit=limit)}


@app.get("/runs/latest")
def get_latest_run(request: Request):
    _require_authenticated_user(request)
    latest = get_latest_run_log()
    if not latest:
        raise HTTPException(status_code=404, detail="No run logs found yet.")
    return latest


@app.post("/generate-form")
async def generate_form(
    request: Request,
    requirement: str = Form(...),
    platforms: list[str] = Form([]),
    modules: list[str] = Form([]),
    pages: list[str] = Form([]),
    test_types: list[str] = Form([]),
    update_comment: str = Form(None),
    output_filename: str = Form(None),
):
    from models.test_request import TestGenerationRequest
    _require_authenticated_user(request)

    started_at = perf_counter()
    requirement = _clean_requirement(requirement)
    run_request_payload = _build_run_request_payload(
        requirement=requirement,
        template="manual",
        platforms=platforms,
        modules=modules,
        pages=pages,
        test_types=test_types,
        output_filename=output_filename,
        update_comment=update_comment,
    )

    try:
        if not requirement:
            raise HTTPException(status_code=400, detail="Requirement cannot be empty")

        selected_platforms = [p for p in platforms if p]
        if not selected_platforms:
            raise HTTPException(status_code=400, detail="At least one platform must be selected.")

        # Build request object manually
        request_obj = TestGenerationRequest(
            requirement=requirement,
            platforms=selected_platforms,
            modules=modules,
            pages=pages,
            test_types=test_types,
            update_comment=update_comment,
            template="manual",
        )

        tests = generate_full_test_suite(request_obj, update_comment=update_comment)

        # Filename logic
        if output_filename:
            filename = f"{output_filename}.xlsx"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_{timestamp}.xlsx"

        file_path = UPLOAD_DIR / filename

        export_to_excel(
            tests,
            template_type="manual",
            output_path=file_path
        )

        log_generation_run(
            endpoint="/generate-form",
            status="success",
            request_payload=run_request_payload,
            result_payload={
                "file_name": filename,
                "download_url": f"/download/{filename}",
                "generated_summary": summarize_tests(tests),
            },
            duration_ms=int((perf_counter() - started_at) * 1000),
        )

        return FileResponse(
            file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except HTTPException as exc:
        log_generation_run(
            endpoint="/generate-form",
            status="failed",
            request_payload=run_request_payload,
            error=str(exc.detail),
            duration_ms=int((perf_counter() - started_at) * 1000),
        )
        raise
    except Exception as exc:
        log_generation_run(
            endpoint="/generate-form",
            status="failed",
            request_payload=run_request_payload,
            error=str(exc),
            duration_ms=int((perf_counter() - started_at) * 1000),
        )
        raise
    
@app.post("/generate-simple")
async def generate_simple(request: Request, requirement: str = Form(...)):
    _require_authenticated_user(request)

    from models.test_request import TestGenerationRequest

    started_at = perf_counter()
    requirement = _clean_requirement(requirement)
    run_request_payload = _build_run_request_payload(
        requirement=requirement,
        template="manual",
    )

    try:
        if not requirement:
            raise HTTPException(status_code=400, detail="Requirement cannot be empty")

        request_obj = TestGenerationRequest(
            requirement=requirement,
            template="manual"
        )

        tests = generate_full_test_suite(request_obj)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_{timestamp}.xlsx"
        file_path = UPLOAD_DIR / filename

        export_to_excel(
            tests,
            template_type="manual",
            output_path=file_path
        )

        log_generation_run(
            endpoint="/generate-simple",
            status="success",
            request_payload=run_request_payload,
            result_payload={
                "file_name": filename,
                "download_url": f"/download/{filename}",
                "generated_summary": summarize_tests(tests),
            },
            duration_ms=int((perf_counter() - started_at) * 1000),
        )

        return FileResponse(
            file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except HTTPException as exc:
        log_generation_run(
            endpoint="/generate-simple",
            status="failed",
            request_payload=run_request_payload,
            error=str(exc.detail),
            duration_ms=int((perf_counter() - started_at) * 1000),
        )
        raise
    except Exception as exc:
        log_generation_run(
            endpoint="/generate-simple",
            status="failed",
            request_payload=run_request_payload,
            error=str(exc),
            duration_ms=int((perf_counter() - started_at) * 1000),
        )
        raise


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
