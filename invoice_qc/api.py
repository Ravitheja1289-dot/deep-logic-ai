"""
FastAPI endpoints for invoice extraction and validation.
"""

import tempfile
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import logging

from invoice_qc.extractor import extract_invoice
from invoice_qc.validator import validate_batch

logger = logging.getLogger(__name__)

# Maximum upload size per file (bytes). Set to 10 MB by default.
MAX_UPLOAD_SIZE = 10 * 1024 * 1024

app = FastAPI(title="Invoice QC API", version="1.0.0")

# Allow cross-origin requests so the deployed Streamlit frontend can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your Streamlit domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Dictionary with status "ok"
    """
    return {"status": "ok"}


@app.post("/validate-json")
async def validate_json(invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a batch of invoices from JSON input.
    
    Args:
        invoices: List of invoice dictionaries to validate.
    
    Returns:
        Validation result from validate_batch, containing per_invoice results and summary.
    """
    try:
        if not isinstance(invoices, list):
            raise HTTPException(status_code=400, detail="Input must be a list of invoice objects")
        
        validation_result = validate_batch(invoices)
        return validation_result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@app.post("/extract-and-validate-pdfs")
async def extract_and_validate_pdfs(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """
    Extract invoice data from uploaded PDF files and validate them.
    
    Args:
        files: List of uploaded PDF files.
    
    Returns:
        Dictionary with:
        - extracted: List of extracted invoice dictionaries
        - validation: Validation result from validate_batch
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    extracted_invoices = []
    temp_files = []
    
    try:
        # Process each uploaded file
        for file in files:
            # Validate file type
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{file.filename}' is not a PDF"
                )
            
            # Create temporary file for PDF
            # Note: tempfile will auto-cleanup when context exits
            content = await file.read()

            # Enforce upload size
            if len(content) > MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=413, detail=f"File '{file.filename}' exceeds maximum size of {MAX_UPLOAD_SIZE} bytes")

            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file_path = temp_file.name
                temp_files.append(temp_file_path)
                temp_file.write(content)
                temp_file.flush()
            
            # Extract invoice data
            try:
                invoice_data = extract_invoice(temp_file_path)
                extracted_invoices.append(invoice_data)
            except Exception as e:
                # Continue processing other files even if one fails
                extracted_invoices.append({
                    'source_file': file.filename,
                    'error': f"Extraction failed: {str(e)}"
                })
        
        # Validate extracted invoices (filter out error entries)
        valid_invoices = [inv for inv in extracted_invoices if 'error' not in inv]
        
        if valid_invoices:
            validation_result = validate_batch(valid_invoices)
        else:
            # Return empty validation result if no valid invoices
            validation_result = {
                'per_invoice': [],
                'summary': {
                    'total_invoices': 0,
                    'valid_count': 0,
                    'invalid_count': 0,
                    'error_counts': {},
                    'duplicate_groups': 0
                }
            }
        
        return {
            'extracted': extracted_invoices,
            'validation': validation_result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    finally:
        # Cleanup temporary files
        # Note: tempfile should auto-delete, but explicit cleanup for safety
        for temp_file_path in temp_files:
            try:
                Path(temp_file_path).unlink(missing_ok=True)
            except Exception:
                pass  # Ignore cleanup errors


