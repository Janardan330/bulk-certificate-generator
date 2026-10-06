import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas

class CertificateGeneratorService:
    @staticmethod
    def generate_pdf(
        recipient_name: str,
        title: str,
        event_name: str,
        issue_date: str,
        certificate_code: str,
        output_path: str,
        fail_trigger: bool = False
    ) -> str:
        """
        Generates a PDF certificate document using ReportLab.
        If fail_trigger is True, simulates a generation failure.
        """
        if fail_trigger:
            raise ValueError(f"Simulated certificate generation failure for recipient: {recipient_name}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # A4 Landscape dimensions: width = 841.89, height = 595.27 points
        width, height = landscape(A4)
        c = canvas.Canvas(output_path, pagesize=landscape(A4))
        
        # Background
        c.setFillColor(colors.HexColor("#FAFAFA"))
        c.rect(0, 0, width, height, fill=True, stroke=False)
        
        # Outer Navy Border
        c.setLineWidth(5)
        c.setStrokeColor(colors.HexColor("#1A365D"))
        c.rect(25, 25, width - 50, height - 50, fill=False, stroke=True)
        
        # Inner Gold Accent Line
        c.setLineWidth(1.5)
        c.setStrokeColor(colors.HexColor("#D69E2E"))
        c.rect(32, 32, width - 64, height - 64, fill=False, stroke=True)
        
        # CERTIFICATE HEADER / TITLE
        c.setFont("Helvetica-Bold", 30)
        c.setFillColor(colors.HexColor("#1A365D"))
        c.drawCentredString(width / 2.0, height - 110, title.upper())
        
        # Subtitle
        c.setFont("Helvetica", 14)
        c.setFillColor(colors.HexColor("#4A5568"))
        c.drawCentredString(width / 2.0, height - 160, "This is to certify that")
        
        # Recipient Name
        c.setFont("Helvetica-Bold", 26)
        c.setFillColor(colors.HexColor("#2B6CB0"))
        c.drawCentredString(width / 2.0, height - 215, recipient_name.upper())
        
        # Underline accent
        c.setLineWidth(1)
        c.setStrokeColor(colors.HexColor("#CBD5E0"))
        c.line(width / 2.0 - 160, height - 230, width / 2.0 + 160, height - 230)
        
        # Subtext
        c.setFont("Helvetica", 14)
        c.setFillColor(colors.HexColor("#4A5568"))
        c.drawCentredString(width / 2.0, height - 270, "has successfully participated in and completed")
        
        # Event Name
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.HexColor("#2D3748"))
        c.drawCentredString(width / 2.0, height - 315, event_name)
        
        # Issue Date
        c.setFont("Helvetica", 12)
        c.setFillColor(colors.HexColor("#718096"))
        date_str = f"Date: {issue_date}" if issue_date else "Date: N/A"
        c.drawCentredString(width / 2.0, height - 380, date_str)
        
        # Certificate Verification ID
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.HexColor("#1A365D"))
        c.drawCentredString(width / 2.0, height - 440, f"Certificate ID: {certificate_code}")
        
        c.showPage()
        c.save()
        return output_path
