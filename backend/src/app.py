from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any
import base64
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

class AuditResponse(BaseModel):
    status: str
    screenshot: str # Base64
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
        
        # Add the URL to the report so it appears in the PDF
        report['url'] = request.url

        path = r"C:\Users\tanma\OneDrive\Desktop\floto_project\backend\report.pdf"
        generate_audit_pdf(report, path)
        send_audit_email(path)
        # 3. Return the payload
        return {
            "status": "success",
            "screenshot": crawl_data['screenshot'],
            "report": report
        }

    except Exception as e:
        print(f"Error during audit: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)