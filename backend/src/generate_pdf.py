import resend
import base64
import os
from dotenv import load_dotenv
load_dotenv()

resend.api_key = os.getenv("RESEND_KEY")
HARDCODED_REPORT_EMAIL = "batmantanmay22@gmail.com"

from fpdf import FPDF

class AuditPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 20)
        self.cell(0, 10, "Conversion Audit Report", ln=True, align="L")
        self.set_draw_color(59, 130, 246)
        self.line(10, 22, 200, 22)
        self.ln(10)

def clean(text):
    """Helper to safely convert any input to a latin-1 compatible string."""
    if text is None:
        return ""
    return str(text).encode('latin-1', 'ignore').decode('latin-1')

def generate_audit_pdf(report_data: dict, output_path: str):
    pdf = AuditPDF()
    pdf.add_page()
    
    # 1. Overall Score Box
    pdf.set_fill_color(17, 24, 39)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 16)
    
    # Clean the score specifically
    score_val = report_data.get('overall_score', 0)
    score_text = f"Overall Score: {score_val}"
    # Note: ln=1 moves to next line
    pdf.cell(60, 15, clean(score_text), ln=1, align="C", fill=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    pdf.set_font("helvetica", "I", 10)
    
    # Safely handle the URL
    url_text = f"Analysis for: {report_data.get('url', 'N/A')}"
    pdf.cell(0, 10, clean(url_text), ln=1)
    
    # 2. Funnel Section
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Funnel Analysis", ln=1)
    
    for stage in report_data.get('funnel_data', []):
        pdf.set_font("helvetica", "B", 11)
        title = f"{stage.get('stage')} - {stage.get('status')}"
        pdf.cell(0, 7, clean(title), ln=1)
        
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 5, clean(stage.get('value', '')))
        pdf.ln(3)

    # 3. Recommendations
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Top Recommendations", ln=1)
    
    pdf.set_font("helvetica", "", 10)
    for rec in report_data.get('top_recommendations', []):
        pdf.multi_cell(0, 6, clean(f"- {rec}"))
        pdf.ln(2)

    pdf.output(output_path)
    return output_path



def send_audit_email(pdf_path: str):
    recipient = HARDCODED_REPORT_EMAIL

    if not resend.api_key:
        raise ValueError("RESEND_KEY is not configured.")

    # 1. Read and encode the PDF file
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()
        encoded_content = base64.b64encode(pdf_content).decode()

    # 2. Send the email
    params = {
        "from": "onboarding@resend.dev",
        "to": recipient,
        "subject": "Your Conversion Audit Report is Ready",
        "html": """
            <h1>Audit Complete!</h1>
            <p>Your AI-powered conversion audit has been generated successfully. Download report of view dashboard on site</p>
            <p><strong>Attached:</strong> Detailed PDF report with strategic recommendations.</p>
        """,
        "attachments": [
            {
                "filename": "Conversion_Audit_Report.pdf",
                "content": encoded_content,
            }
        ]
    }

    response = resend.Emails.send(params)
    print(f"Email sent successfully!")
    return response

