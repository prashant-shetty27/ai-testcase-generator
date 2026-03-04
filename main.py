import shutil
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

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=BASE_DIR / "web/templates")

# -------------------------
# GENERATE TESTS
# -------------------------
@app.post("/generate-tests")
def generate(request: TestGenerationRequest):

    if not request.requirement.strip():
        raise HTTPException(status_code=400, detail="Requirement cannot be empty")

    # -------- UPDATE FLOW --------
    if request.existing_filename:
        file_path = UPLOAD_DIR / request.existing_filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        raw_cases = read_existing_testcases(file_path)
        existing_cases = normalize_existing_testcases(raw_cases)

        tests = generate_full_test_suite(
            request,
            existing_cases=existing_cases,
            update_comment=request.update_comment
        )

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
    return templates.TemplateResponse("index.html", {"request": request})

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

    # Build request object manually
    request_obj = TestGenerationRequest(
        requirement=requirement,
        platforms=platforms,
        modules=modules,
        pages=pages,
        test_types=test_types,
    )

    tests = generate_full_test_suite(request_obj)

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