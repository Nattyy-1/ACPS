import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF


def _draw_qr(c, x, y, url, size=80):
    qr_code = qr.QrCodeWidget(url)
    d = Drawing(size, size)
    d.add(qr_code)
    renderPDF.draw(d, c, x, y)


def generate_planning_consent_pdf(application, permit, verify_url=""):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, height - 50, "PLANNING CONSENT")
    c.setFont("Helvetica", 9)
    c.drawString(40, height - 68, "Issued under Building Proclamation 624/2009")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - 95, "Permit Details")
    y = height - 115
    for label, val in [
        ("Permit Number", permit.permit_number),
        ("ARN", application.arn),
        ("Applicant", application.applicant.full_name),
        ("Plot Address", application.plot_address),
        ("Subcity", application.subcity_id),
        ("Woreda", application.woreda),
        ("Building Category", f"Category {application.building_category}"),
        ("Height (m)", str(application.height_m)),
        ("Floors Above Ground", str(application.floors_above)),
        ("Floors Below Ground", str(application.floors_below)),
        ("Floor Area (sqm)", str(application.floor_area_sqm)),
        ("Intended Use", application.intended_use),
        ("Architect", f"{application.architect_name} ({application.architect_license})"),
        ("Issue Date", permit.issue_date.strftime("%Y-%m-%d")),
        ("Expiry Date", permit.expiry_date.strftime("%Y-%m-%d")),
    ]:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, f"{label}:")
        c.setFont("Helvetica", 9)
        c.drawString(170, y, str(val))
        y -= 16

    if verify_url:
        _draw_qr(c, 40, y - 100, verify_url)
        c.setFont("Helvetica", 8)
        c.drawString(40, y - 110, "Scan to verify permit validity")

    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y - 160, "Authorized Signature:")
    c.setFont("Helvetica", 9)
    c.drawString(40, y - 178, "_________________________")
    c.drawString(40, y - 193, "Senior Approving Officer")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def generate_construction_permit_pdf(application, permit, verify_url=""):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, height - 50, "CONSTRUCTION PERMIT")
    c.setFont("Helvetica", 9)
    c.drawString(40, height - 68, "Issued under Building Proclamation 624/2009 and Regulation 243/2011")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - 95, "Permit Details")
    y = height - 115
    for label, val in [
        ("Permit Number", permit.permit_number),
        ("ARN", application.arn),
        ("Applicant", application.applicant.full_name),
        ("Plot Address", application.plot_address),
        ("Subcity", application.subcity_id),
        ("Woreda", application.woreda),
        ("Building Category", f"Category {application.building_category}"),
        ("Height (m)", str(application.height_m)),
        ("Floors Above Ground", str(application.floors_above)),
        ("Floors Below Ground", str(application.floors_below)),
        ("Floor Area (sqm)", str(application.floor_area_sqm)),
        ("Intended Use", application.intended_use),
        ("Architect", f"{application.architect_name} ({application.architect_license})"),
        ("Contractor", application.contractor_name or "Not specified"),
        ("Issue Date", permit.issue_date.strftime("%Y-%m-%d")),
        ("Expiry Date", permit.expiry_date.strftime("%Y-%m-%d")),
    ]:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, f"{label}:")
        c.setFont("Helvetica", 9)
        c.drawString(170, y, str(val))
        y -= 16

    y -= 10
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Conditions:")
    y -= 16
    c.setFont("Helvetica", 9)
    for cond in [
        "1. Construction must comply with approved architectural and structural drawings.",
        "2. Site safety measures must be maintained throughout construction.",
        "3. Inspections must be scheduled at required milestones.",
        "4. Any deviations require prior written approval.",
        "5. This permit is valid for 12 months from date of issue.",
    ]:
        c.drawString(40, y, cond)
        y -= 14

    y -= 20
    if verify_url:
        _draw_qr(c, 40, y - 80, verify_url)
        c.setFont("Helvetica", 8)
        c.drawString(40, y - 90, "Scan to verify permit validity")

    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y - 140, "Authorized Signature:")
    c.setFont("Helvetica", 9)
    c.drawString(40, y - 158, "_________________________")
    c.drawString(40, y - 173, "Senior Approving Officer")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf
