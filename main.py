from fastapi import FastAPI
from excel_exporter import export_to_excel
from services.test_generation_service import generate_full_test_suite

app = FastAPI()

@app.post("/generate-tests")
def generate(requirement: str, template: str = "manual"):

    tests = generate_full_test_suite(requirement)
    file_path = export_to_excel(tests, template)

    return {
        "message": "Generated successfully",
        "template_used": template,
        "excel_file": file_path
    }