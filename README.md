# Invoice QC Service

A production-ready invoice quality control system for B2B PDF invoices with variable layouts. The service extracts invoice data from PDFs using regex heuristics and pdfplumber, then validates extracted data against business rules, format checks, and anomaly detection. It provides both CLI and REST API interfaces for batch processing.

## What I Built

- **Extractor Module** (`invoice_qc/extractor.py`): PDF text and table extraction using pdfplumber with regex-based field extraction
- **Validator Module** (`invoice_qc/validator.py`): Deterministic validation with error tokens for completeness, format, business rules, anomalies, and sanity checks
- **CLI Interface** (`invoice_qc/cli.py`): Typer-based commands for extract, validate, and full-run workflows
- **REST API** (`invoice_qc/api.py`): FastAPI endpoints for JSON validation and PDF upload/validation
- **Regex Patterns** (`invoice_qc/regex_patterns.py`): Robust extraction patterns with named groups for common invoice variants

## Schema & Validation Design

### JSON Schema Example

```json
{
  "invoice_id": "INV-2024-001234",
  "invoice_number": "INV-2024-001234",
  "invoice_date": "2024-03-15",
  "due_date": "2024-04-14",
  "supplier_name": "Acme Corp",
  "supplier_address": "123 Business St, City, State 12345",
  "supplier_tax_id": "12-3456789",
  "buyer_name": "Tech Industries Ltd",
  "buyer_address": "456 Corporate Ave, City, State 67890",
  "buyer_tax_id": "98-7654321",
  "currency": "USD",
  "subtotal": 15000.00,
  "tax_amount": 1200.00,
  "total_amount": 16200.00,
  "payment_terms": "Net 30",
  "line_items": [
    {
      "item_code": "SKU-001",
      "description": "Professional Services",
      "quantity": 100,
      "unit_price": 150.00,
      "line_total": 15000.00
    }
  ]
}
```

### Validation Rules

**Completeness Checks:**
1. Required fields present (invoice_number, invoice_date, supplier_name, buyer_name, total_amount) - *Core invoice identity and financial data are mandatory for processing*
2. Line items non-empty - *Invoices without line items are invalid business documents*
3. Line item completeness - *Incomplete line items cannot be validated or processed*

**Format Checks:**
4. Date format (ISO 8601 YYYY-MM-DD) - *Standardized date format enables reliable date arithmetic and comparisons*
5. Numeric precision (max 2 decimal places) - *Currency precision standards prevent rounding errors*
6. Currency code (ISO 4217) - *Standard currency codes ensure proper financial processing*
7. Tax ID format validation - *Tax ID format validation prevents data entry errors*

**Business Logic Checks:**
8. Date consistency (due_date >= invoice_date) - *Due dates cannot precede invoice dates in valid business transactions*
9. Amount consistency (total_amount = subtotal + tax_amount, 0.5% tolerance) - *Invoice totals must mathematically reconcile to prevent accounting errors*
10. Line item totals (sum of line_items ≈ subtotal, 0.5% tolerance) - *Line item aggregation must match invoice subtotal for accuracy*

**Anomaly/Duplicate Checks:**
11. Duplicate invoice detection (invoice_number + supplier_tax_id + invoice_date) - *Duplicate invoice numbers indicate potential duplicate payments or data errors*
12. Unusual amount detection - *Statistical outliers may indicate errors or fraud*
13. Future-dated invoice check - *Future-dated invoices beyond reasonable buffer suggest data extraction errors*

**Sanity Checks:**
14. Positive amounts - *Negative amounts require special handling and should be flagged*
15. Reasonable quantity ranges - *Extreme quantities likely indicate extraction errors*
16. Valid date ranges - *Out-of-range dates indicate extraction or system errors*

**Field Requirements:**
- **Required**: invoice_number, invoice_date, supplier_name, buyer_name, total_amount, line_items (non-empty)
- **Optional**: due_date, supplier_address, supplier_tax_id, buyer_address, buyer_tax_id, currency (defaults to "USD"), subtotal, tax_amount, payment_terms
- **Internal invoice_id fallback**: `{supplier_name}_{invoice_number}_{invoice_date}` (normalized: uppercase, alphanumeric only, spaces→underscores)

## Architecture / Folder Structure

```
deep-logic-ai/
├── invoice_qc/
│   ├── __init__.py
│   ├── extractor.py          # PDF extraction with pdfplumber
│   ├── validator.py           # Validation rules and batch processing
│   ├── cli.py                 # Typer CLI interface
│   ├── api.py                 # FastAPI REST endpoints
│   ├── regex_patterns.py      # Robust extraction patterns
│   └── REGEX_PATTERNS_REFERENCE.md
├── invoice_qc_schema.json     # JSON schema example
├── invoice_qc_validation_rules.md
└── README.md
```

## Setup & Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install pdfplumber python-dateutil typer fastapi uvicorn python-multipart
```

## CLI Usage

### Extract Invoices from PDFs

```bash
python -m invoice_qc.cli extract --pdf-dir ./invoices --output extracted.json
```

### Validate Extracted Invoices

```bash
python -m invoice_qc.cli validate --input extracted.json --report validation_report.json
```

### Full Run (Extract + Validate)

```bash
python -m invoice_qc.cli full-run --pdf-dir ./invoices --report validation_report.json
```

All commands print a summary with total, valid, invalid counts, and top 3 error types. Commands exit with non-zero code if invalid invoices are found.

## API Usage

Start the FastAPI server:

```bash
uvicorn invoice_qc.api:app --reload
```

### Validate JSON Invoices

```bash
curl -X POST "http://localhost:8000/validate-json" \
  -H "Content-Type: application/json" \
  -d @invoices.json
```

### Extract and Validate PDFs

```bash
curl -X POST "http://localhost:8000/extract-and-validate-pdfs" \
  -F "files=@invoice1.pdf" \
  -F "files=@invoice2.pdf"
```

## AI Usage Notes

**Tools Used:**
- Cursor AI (Claude Sonnet 4.5) for code generation, schema design, and validation rule formulation

**Example AI Correction:**
The AI initially suggested using `re.match()` for date extraction, which only matches at the start of strings. I corrected this to `re.search()` to find dates anywhere in the invoice text, significantly improving extraction accuracy for invoices with varied layouts. Additionally, the AI's initial currency extraction only checked for explicit "Currency:" labels, but I enhanced it to also detect currency symbols ($, €, £) and ISO codes anywhere in the document.

## Assumptions & Limitations

**Assumptions:**
- PDFs are text-based (not scanned images)
- Invoices follow common B2B formats with recognizable field labels
- Currency amounts use standard formatting (commas for thousands, dots for decimals)
- Dates are in recognizable formats (MM/DD/YYYY, YYYY-MM-DD, etc.)

**Limitations:**
- Scanned/image-based PDFs require OCR preprocessing (not supported)
- Complex multi-column layouts may have reduced extraction accuracy
- Regex patterns may need tuning for region-specific invoice formats
- Line item extraction relies on pdfplumber table detection quality
- Duplicate detection requires supplier_tax_id for reliable matching

## Integration with Larger Systems
 
This service is designed to be a composable part of a larger document processing pipeline.
 
- **API Integration**: Downstream systems (e.g., an ERP or AP automation platform) can call the `POST /validate-json` endpoint to validate invoice data extracted by other OCR tools. Alternatively, the `POST /extract-and-validate-pdfs` endpoint can be used as a self-contained extraction service.
- **Event-Driven Architecture**: The CLI can be triggered by file system watchers or cron jobs. For a more robust setup, you could wrap the CLI or API calls in a worker (e.g., Celery, temporal.io) that consumes messages from a queue (SQS, RabbitMQ) whenever a new invoice is uploaded to S3.
- **Containerization**: The application is stateless and can be easily containerized (Docker) and deployed to Kubernetes or serverless containers (AWS Fargate, Google Cloud Run). Health checks (`/health`) are ready for orchestrator liveness probes.
 
## Video Demo

[Google Drive Link - Placeholder](https://drive.google.com/your-demo-link-here)

*Demo video showing:*
- PDF extraction workflow
- Validation error reporting
- CLI and API usage examples
- Batch processing capabilities


