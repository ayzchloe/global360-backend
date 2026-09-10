import io
from datetime import date
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def generate_certificate_pdf(
    student_name: str,
    course_name: str,
    certificate_id: str,
    issued_date: str | date,
    grade: str = "Distinction",
    skills: str = None,
) -> bytes:
    """
    Generates an official, publication-ready PDF certificate for Global360.
    Returns the binary content as bytes.
    """
    buffer = io.BytesIO()
    # Landscape Letter: 11 x 8.5 inches = 792 x 612 pt
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    if isinstance(issued_date, date):
        date_str = issued_date.strftime("%B %d, %Y")
    else:
        date_str = str(issued_date)

    # 1. Background Fill
    c.setFillColor(colors.HexColor("#FCFDFD"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # 2. Outer Navy Border
    c.setStrokeColor(colors.HexColor("#0F172A"))
    c.setLineWidth(5)
    c.rect(24, 24, width - 48, height - 48)

    # 3. Inner Gold Border
    c.setStrokeColor(colors.HexColor("#D97706"))
    c.setLineWidth(1.5)
    c.rect(32, 32, width - 64, height - 64)

    # 4. Corner Ornaments (accent marks in corners)
    c.setStrokeColor(colors.HexColor("#D97706"))
    c.setLineWidth(2.5)
    for cx, cy in [(40, 40), (width - 40, 40), (40, height - 40), (width - 40, height - 40)]:
        c.circle(cx, cy, 4, stroke=1, fill=1)

    # 5. Header / Branding
    c.setFillColor(colors.HexColor("#0284C7"))  # Brand Cyan/Sky
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2.0, height - 70, "GLOBAL 360 INSTITUTE OF TECHNOLOGY")

    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2.0, height - 85, "GLOBAL RECOGNITION • INDUSTRY CREDENTIALS • VERIFIED MASTERY")

    # 6. Main Certificate Title
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2.0, height - 130, "CERTIFICATE OF COMPLETION")

    # Thin Divider Line
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(1)
    c.line(width / 2.0 - 140, height - 145, width / 2.0 + 140, height - 145)

    # 7. Subtitle
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica-Oblique", 12)
    c.drawCentredString(width / 2.0, height - 175, "This is proudly presented to")

    # 8. Student Name (Prominent)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2.0, height - 215, student_name.upper())

    # Decorative Underline for Name
    c.setStrokeColor(colors.HexColor("#D97706"))
    c.setLineWidth(1.5)
    name_width = max(len(student_name) * 15, 240)
    c.line(width / 2.0 - name_width / 2.0, height - 224, width / 2.0 + name_width / 2.0, height - 224)

    # 9. Course Description Text
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2.0, height - 252, "for successfully demonstrating competence, professional mastery, and completing the coursework in")

    # 10. Course Name
    c.setFillColor(colors.HexColor("#0369A1"))
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2.0, height - 285, course_name)

    # 11. Grade & Skills
    info_text = f"Standing: {grade}"
    if skills:
        info_text += f"   •   Competencies: {skills}"
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2.0, height - 315, info_text)

    # 12. Bottom Signatures & Seal Section
    y_signatures = 100

    # Left: Academic Director Signature
    c.setStrokeColor(colors.HexColor("#94A3B8"))
    c.setLineWidth(1)
    c.line(100, y_signatures + 25, 260, y_signatures + 25)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(180, y_signatures + 10, "Dr. Robert Vance, Ph.D.")
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(180, y_signatures - 3, "Director of Academic Affairs")

    # Center: Official Global360 Gold Seal
    seal_x = width / 2.0
    seal_y = y_signatures + 18
    c.setFillColor(colors.HexColor("#FEF3C7"))
    c.setStrokeColor(colors.HexColor("#D97706"))
    c.setLineWidth(2)
    c.circle(seal_x, seal_y, 34, stroke=1, fill=1)
    c.setLineWidth(1)
    c.circle(seal_x, seal_y, 30, stroke=1, fill=0)

    c.setFillColor(colors.HexColor("#B45309"))
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(seal_x, seal_y + 8, "GLOBAL360")
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(seal_x, seal_y - 2, "★ VERIFIED ★")
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(seal_x, seal_y - 12, "ACCREDITED")

    # Right: Program Lead Signature
    c.setStrokeColor(colors.HexColor("#94A3B8"))
    c.setLineWidth(1)
    c.line(width - 260, y_signatures + 25, width - 100, y_signatures + 25)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width - 180, y_signatures + 10, "Sarah Jenkins, M.Sc.")
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(width - 180, y_signatures - 3, "Head of Curriculum & Instruction")

    # 13. Footer: Credential ID, Verification Link, Issue Date
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 8)
    c.drawString(45, 45, f"Issued Date: {date_str}")
    c.drawCentredString(width / 2.0, 45, f"Verify authenticity online: https://global360.edu/verify/{certificate_id}")
    c.drawRightString(width - 45, 45, f"Credential ID: {certificate_id}")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def generate_fee_challan_pdf(
    challan_no: str,
    student_name: str,
    program: str,
    title: str,
    amount: float,
    due_date,
    issued_date,
    status: str = "pending",
    payment_method: str = None,
    account_number: str = None,
    instructions: str = None,
) -> bytes:
    """
    Generates a printable Fee Challan / Payment Voucher PDF.
    Returns the binary content as bytes.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    if isinstance(issued_date, date):
        issued_str = issued_date.strftime("%B %d, %Y")
    else:
        issued_str = str(issued_date)
    if isinstance(due_date, date):
        due_str = due_date.strftime("%B %d, %Y")
    else:
        due_str = str(due_date)

    # Background
    c.setFillColor(colors.HexColor("#FFFFFF"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Header band
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(60, height - 60, "GLOBAL360")
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(60, height - 80, "Institute of Technology — Official Fee Challan")

    # Challan number badge
    c.setFillColor(colors.HexColor("#D97706"))
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 60, height - 60, f"Challan #: {challan_no}")

    # Divider
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(1)
    c.line(60, height - 95, width - 60, height - 95)

    # Student info
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, height - 130, "Student:")
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 12)
    c.drawString(130, height - 130, student_name)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, height - 155, "Program:")
    c.setFillColor(colors.HexColor("#334155"))
    c.drawString(130, height - 155, program or "General Studies")

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, height - 180, "Title:")
    c.setFillColor(colors.HexColor("#334155"))
    c.drawString(130, height - 180, title or "Semester Tuition Fee")

    # Amount box
    c.setFillColor(colors.HexColor("#FEF3C7"))
    c.setStrokeColor(colors.HexColor("#D97706"))
    c.setLineWidth(2)
    c.roundRect(width - 200, height - 200, 140, 50, 8, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#B45309"))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width - 130, height - 182, "Amount")
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width - 130, height - 165, f"${amount:,.2f}")

    # Dates
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, height - 240, "Issued Date:")
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 12)
    c.drawString(160, height - 240, issued_str)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, height - 270, "Due Date:")
    c.setFillColor(colors.HexColor("#334155"))
    if status == "paid":
        c.setFillColor(colors.HexColor("#15803D"))
        c.drawString(130, height - 270, f"{due_str}  (PAID)")
    elif status == "overdue":
        c.setFillColor(colors.HexColor("#B91C1C"))
        c.drawString(130, height - 270, f"{due_str}  (OVERDUE)")
    else:
        c.drawString(130, height - 270, due_str)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, height - 300, "Payment Method:")
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 12)
    c.drawString(170, height - 300, payment_method or "Pending")

    # Payment instructions
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, height - 335, "Payment Instructions:")
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 10)
    if instructions:
        c.drawString(60, height - 355, instructions)
    if account_number:
        c.drawString(60, height - 375, f"Account #: {account_number}")

    # Footer
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2.0, 50, "This is a system-generated challan. Verify via your Global360 student dashboard.")
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.setLineWidth(0.5)
    c.line(60, 75, width - 60, 75)
    c.drawCentredString(width / 2.0, 35, f"Page 1 — {challan_no}")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()
