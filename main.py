import re
import shutil
import os
from pathlib import Path
from datetime import datetime
from fastapi import Form, Request, FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from models.test_request import TestGenerationRequest
from services.test_generation_service import generate_full_test_suite
from excel_exporter import (
    export_to_excel,
    read_existing_testcases,
    normalize_existing_testcases
)

app = FastAPI(title="AI Testcase Generator", version="1.0")

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


# -------------------------
# GENERATE TESTS
# -------------------------
@app.post("/generate-tests")
def generate(request: TestGenerationRequest):

    request.requirement = _clean_requirement(request.requirement)
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

        return {
            "message": "Existing testcases updated",
            "download_url": f"/download/{file_path.name}"
        }

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

    return {
        "message": "Generated successfully",
        "download_url": f"/download/{filename}"
    }


# -------------------------
# UPLOAD EXISTING FILE
# -------------------------
@app.post("/upload-testcases")
async def upload_testcases(file: UploadFile = File(...)):

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
def download(filename: str):

    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    response = templates.TemplateResponse("index.html", {"request": request})
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.post("/generate-form")
async def generate_form(
    requirement: str = Form(...),
    platforms: list[str] = Form([]),
    modules: list[str] = Form([]),
    pages: list[str] = Form([]),
    test_types: list[str] = Form([]),
    update_comment: str = Form(None),
    output_filename: str = Form(None),
):
    from models.test_request import TestGenerationRequest

    requirement = _clean_requirement(requirement)
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

    return FileResponse(
        file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
@app.post("/generate-simple")
async def generate_simple(requirement: str = Form(...)):

    from models.test_request import TestGenerationRequest

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

    return FileResponse(
        file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
