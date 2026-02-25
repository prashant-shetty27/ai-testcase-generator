from openpyxl import Workbook
import importlib
from openpyxl.styles import Alignment

def export_to_excel(testcases, template_name="manual"):

    template = importlib.import_module(
        f"templates.{template_name}_template"
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "AI Testcases"

    # headers from template
    ws.append(template.get_headers())

    for category, tests in testcases.items():
        for tc in tests:
            row_data = template.map_testcase(category, tc)
            ws.append(row_data)

# Apply wrap text to the entire row
    for cell in ws[ws.max_row]:
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    file_path = f"generated_testcases_{template_name}.xlsx"
    wb.save(file_path)

    return file_path