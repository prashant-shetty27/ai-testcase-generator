from openpyxl import Workbook, load_workbook
from datetime import datetime
from templates.manual_template import ManualTemplate
from templates.automation_template import AutomationTemplate


def export_to_excel(tests, template_type="manual", output_path=None):

    wb = Workbook()
    ws = wb.active
    ws.title = "Test Cases"

    ws.append([
        "Testcase ID",
        "Priority",
        "Category",
        "Scenario",
        "Steps",
        "Expected Result"
    ])

    template = AutomationTemplate if template_type == "automation" else ManualTemplate

    for category, cases in tests.items():

        if category == "automation_candidates":
            continue

        if not isinstance(cases, list):
            continue

        for tc in cases:
            if not isinstance(tc, dict):
                continue

            ws.append(template.map_testcase(category, tc))

    if output_path:
        file_path = output_path
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = f"generated_testcases_{template_type}_{timestamp}.xlsx"

    wb.save(file_path)
    return file_path


def read_existing_testcases(file_path):
    wb = load_workbook(file_path)
    ws = wb.active

    headers = []
    rows = []

    for idx, row in enumerate(ws.iter_rows(values_only=True)):
        if idx == 0:
            headers = list(row)
            continue

        case = {headers[i]: value for i, value in enumerate(row)}
        rows.append(case)

    return rows


def normalize_existing_testcases(raw_cases):
    normalized = []

    for row in raw_cases:
        normalized.append({
            "testcase_id": row.get("Testcase ID"),
            "priority": row.get("Priority", "P1"),
            "scenario": row.get("Scenario"),
            "steps": row.get("Steps", "").split("\n"),
            "expected_result": row.get("Expected Result")
        })

    return normalized