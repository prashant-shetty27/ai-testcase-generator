from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os

from models.test_request import TestGenerationRequest
from services.test_generation_service import generate_full_test_suite
from excel_exporter import export_to_excel

app = FastAPI()

templates = Jinja2Templates(directory="web/templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate-tests")
def generate(request: TestGenerationRequest):

    if not request.requirement or not request.requirement.strip():
        return {"error": "Requirement cannot be empty"}

    tests = generate_full_test_suite(request)
    file_path = export_to_excel(tests, request.template)

    return {
        "message": "Generated successfully",
        "template_used": request.template,
        "excel_file": file_path
    }

@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(".", filename)
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )