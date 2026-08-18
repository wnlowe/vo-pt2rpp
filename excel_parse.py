from openpyxl import load_workbook

def read_excel(path: str) -> dict:
    wb = load_workbook(path)
    sheet = wb.active
    columns = sheet.iter_cols(max_row=1)
    print(columns)
