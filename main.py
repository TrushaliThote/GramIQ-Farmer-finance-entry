from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

if not os.path.exists("reports"):
    os.makedirs("reports")

# ---------- HTML FORM ----------
@app.get("/", response_class=HTMLResponse)
async def form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

# ---------- PDF GENERATION ----------
@app.post("/generate")
async def generate(
    request: Request,
    farmer_name: str = Form(...),
    crop_name: str = Form(...),
    season: str = Form(...),
    acres: float = Form(...),
    sow_date: str = Form(...),
    harvest_date: str = Form(...),
    location: str = Form(...),
    expenses: str = Form(...),
    incomes: str = Form(...),
):

    # Parse multi-row entries
    def parse_rows(raw):
        rows = []
        for line in raw.split("\n"):
            cols = [x.strip() for x in line.split(",")]
            if len(cols) >= 3:
                rows.append(cols)
        return rows

    expense_rows = parse_rows(expenses)
    income_rows = parse_rows(incomes)

    # Summary calculations
    total_expense = sum(float(r[1]) for r in expense_rows)
    total_income = sum(float(r[1]) for r in income_rows)
    profit = total_income - total_expense
    cost_per_acre = total_expense / acres

    # ---------- CHART ----------
    labels = ["Income", "Expense"]
    values = [total_income, total_expense]
    plt.figure()
    plt.bar(labels, values)
    chart_path = "static/chart.png"
    plt.savefig(chart_path)
    plt.close()

    # ---------- PDF SETUP ----------
    filename = f"reports/{crop_name}_{season}_{datetime.now().year}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    flow = []

    # HEADER TEXT
    flow.append(Paragraph(f"<b>{crop_name} - {acres} Acres - {season}</b>", styles["Title"]))
    flow.append(Paragraph(f"Report generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}", styles["Normal"]))
    flow.append(Paragraph(f"Farmer: {farmer_name}", styles["Normal"]))
    flow.append(Spacer(1, 12))

    # ---------- SUMMARY ----------
    flow.append(Paragraph("<b>Section 1: Finance Summary</b>", styles["Heading2"]))
    summary = [
        ["Total Income", total_income],
        ["Total Expense", total_expense],
        ["Profit / Loss", profit],
        ["Cost per Acre", round(cost_per_acre, 2)]
    ]
    flow.append(Table(summary))
    flow.append(Spacer(1, 12))

    # CHART
    flow.append(Image(chart_path, width=300, height=200))
    flow.append(Spacer(1, 20))

    # ---------- EXPENSE TABLE ----------
    flow.append(Paragraph("<b>Section 3: Expense Breakdown</b>", styles["Heading2"]))
    exp_table = [["Category", "Amount", "Date", "Description"]] + expense_rows
    flow.append(Table(exp_table))
    flow.append(Spacer(1, 15))

    # ---------- INCOME TABLE ----------
    flow.append(Paragraph("<b>Section 4: Income Breakdown</b>", styles["Heading2"]))
    inc_table = [["Category", "Amount", "Date", "Description"]] + income_rows
    flow.append(Table(inc_table))
    flow.append(Spacer(1, 15))

    # ---------- LEDGER ----------
    flow.append(Paragraph("<b>Section 5: Ledger</b>", styles["Heading2"]))
    ledger = [["Date", "Particulars", "Type", "Description", "Amount"]]

    for r in expense_rows:
        ledger.append([r[2], r[0], "Expense", r[3] if len(r) > 3 else "", r[1]])
    for r in income_rows:
        ledger.append([r[2], r[0], "Income", r[3] if len(r) > 3 else "", r[1]])

    flow.append(Table(ledger))
    flow.append(Spacer(1, 15))

    doc.build(flow)

    return FileResponse(
        filename,
        media_type="application/pdf",
        filename=os.path.basename(filename)
    )
