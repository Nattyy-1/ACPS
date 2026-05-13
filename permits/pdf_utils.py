import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.lib.utils import ImageReader


def _draw_qr(c, x, y, url, size=80):
    qr_code = qr.QrCodeWidget(url)
    d = Drawing(size, size)
    d.add(qr_code)
    renderPDF.draw(d, c, x, y)


def _draw_signature(c, x, y, signature_path=None, label="Authorized Signature:"):
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, label)
    if signature_path and os.path.exists(signature_path):
        try:
            img = ImageReader(signature_path)
            c.drawImage(img, x, y - 35, width=120, height=35, preserveAspectRatio=True)
        except Exception:
            c.setFont("Helvetica", 9)
            c.drawString(x, y - 18, "_________________________")
    else:
        c.setFont("Helvetica", 9)
        c.drawString(x, y - 18, "_________________________")
    c.setFont("Helvetica", 9)
    c.drawString(x, y - 40, "Senior Approving Officer")
def generate_planning_consent_pdf(application, permit, verify_url="", signature_path=None):
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

    _draw_signature(c, 40, y - 160, signature_path)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def generate_construction_permit_pdf(application, permit, verify_url="", signature_path=None):
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

    _draw_signature(c, 40, y - 140, signature_path)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def generate_completion_certificate_pdf(application, permit, verify_url="", signature_path=None):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, height - 50, "COMPLETION CERTIFICATE")
    c.setFont("Helvetica", 9)
    c.drawString(40, height - 68, "Issued under Building Proclamation 624/2009 and Regulation 243/2011")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - 95, "Certificate Details")
    y = height - 115
    construction_permit = application.permits.filter(permit_type="CONSTRUCTION").first()
    for label, val in [
        ("Certificate Number", permit.permit_number),
        ("ARN", application.arn),
        ("Permit Number", construction_permit.permit_number if construction_permit else "N/A"),
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
        ("Contractor", application.contractor_name or "Not specified"),
        ("Completion Date", permit.issue_date.strftime("%Y-%m-%d")),
        ("Issue Date", permit.issue_date.strftime("%Y-%m-%d")),
    ]:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, f"{label}:")
        c.setFont("Helvetica", 9)
        c.drawString(170, y, str(val))
        y -= 16

    y -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Certification Statement:")
    y -= 16
    c.setFont("Helvetica", 9)
    statement = (
        "This is to certify that the building construction has been completed "
        "in accordance with the approved plans and specifications, and complies "
        "with the Building Proclamation 624/2009 and relevant regulations."
    )
    c.drawString(40, y, statement[:80])
    c.drawString(40, y - 14, statement[80:])

    y -= 40
    if verify_url:
        _draw_qr(c, 40, y - 80, verify_url)
        c.setFont("Helvetica", 8)
        c.drawString(40, y - 90, "Scan to verify certificate validity")

    _draw_signature(c, 40, y - 150, signature_path)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf
