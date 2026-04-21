from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import base64
import os
from generate_pdf import generate_audit_pdf, send_audit_email

# Import your existing logic
from crawler import capture_conversion_context
from graph import run_audit

app = FastAPI(title="Conversion Intel API")

# Enable CORS so your Next.js frontend can talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHEMAS ---
class AuditRequest(BaseModel):
    url: str
    send_email: bool = False

class AuditResponse(BaseModel):
    status: str
    screenshot: str # Base64
    report: Dict[str, Any]
    email_sent: bool = False
    email_message: Optional[str] = None

class EmailReportRequest(BaseModel):
    report: Dict[str, Any]

# --- ENDPOINTS ---

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/audit", response_model=AuditResponse)
async def perform_audit(request: AuditRequest):
    """
    Trigger the full pipeline: 
    1. Crawl & Screenshot 
    2. LangGraph Analysis
    3. Return Structured Report
    """
    try:
        # 1. Crawl the site
        print(f"Starting crawl for: {request.url}")
        crawl_data = await capture_conversion_context(str(request.url))
        
        if not crawl_data or not crawl_data.get('markdown'):
            raise HTTPException(status_code=400, detail="Could not extract content from URL")

        try:
            screenshot_data = crawl_data['screenshot']
            # Decode the base64 string
            image_bytes = base64.b64decode(screenshot_data)
            
            # Save it to the backend folder
            file_name = "latest_audit_screenshot.png"
            with open(file_name, "wb") as f:
                f.write(image_bytes)
            print(f"✅ Screenshot saved successfully as {file_name}")
        except Exception as e:
            print(f"❌ Failed to save screenshot: {e}")
            
        # 2. Run the LangGraph Audit
        print("Crawl successful. Running AI Audit...")
        report = await run_audit(crawl_data)
        
        # Add the URL to the report for optional PDF generation later
        report['url'] = request.url
        email_sent = False
        email_message = None
        if request.send_email:
            try:
                pdf_path = os.path.join(os.getcwd(), "report.pdf")
                generate_audit_pdf(report, pdf_path)
                send_audit_email(pdf_path)
                email_sent = True
                email_message = "Report emailed successfully."
            except Exception as email_error:
                email_message = f"Audit completed, but email failed: {str(email_error)}"

        # 3. Return the payload
        return {
            "status": "success",
            "screenshot": crawl_data['screenshot'],
            "report": report,
            "email_sent": email_sent,
            "email_message": email_message
        }

    except Exception as e:
        print(f"Error during audit: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-report")
async def send_report(request: EmailReportRequest):
    try:
        path = os.path.join(os.getcwd(), "report.pdf")
        generate_audit_pdf(request.report, path)
        response = send_audit_email(path)
        return {"status": "success", "email_response": response}
    except Exception as e:
        print(f"Error while sending report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)