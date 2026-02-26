from openpyxl import Workbook
from datetime import datetime
from templates.manual_template import ManualTemplate
from templates.automation_template import AutomationTemplate

def export_to_excel(tests, template_type="manual"):

    wb = Workbook()
    ws = wb.active
    ws.title = "Test Cases"

    # Header
    ws.append(["Testcase ID", "Category", "Scenario", "Steps", "Expected Result"])

    # Choose template
    if template_type == "automation":
        template = AutomationTemplate
    else:
        template = ManualTemplate

    # Fill rows
    for category, cases in tests.items():
        for tc in cases:
            row_data = template.map_testcase(category, tc)
            ws.append(row_data)

    # Unique filename to avoid Windows lock
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = f"generated_testcases_{template_type}_{timestamp}.xlsx"

    wb.save(file_path)
    return file_path