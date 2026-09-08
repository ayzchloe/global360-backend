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
