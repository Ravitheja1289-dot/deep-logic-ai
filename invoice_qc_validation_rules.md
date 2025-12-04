# Invoice QC Validation Rules

## JSON Schema Example
See `invoice_qc_schema.json` for the complete schema structure.

## Validation Rules

### Completeness Checks
1. **Required fields present**: invoice_number, invoice_date, supplier_name, buyer_name, total_amount must exist. *Rationale: Core invoice identity and financial data are mandatory for processing.*
2. **Line items non-empty**: At least one line_item must be present. *Rationale: Invoices without line items are invalid business documents.*
3. **Line item completeness**: Each line_item must have description, quantity, unit_price, and line_total. *Rationale: Incomplete line items cannot be validated or processed.*

### Format Checks
4. **Date format**: invoice_date and due_date must be ISO 8601 (YYYY-MM-DD). *Rationale: Standardized date format enables reliable date arithmetic and comparisons.*
5. **Numeric precision**: All monetary fields (subtotal, tax_amount, total_amount, unit_price, line_total) must be numeric with max 2 decimal places. *Rationale: Currency precision standards prevent rounding errors.*
6. **Currency code**: currency must be a valid ISO 4217 3-letter code. *Rationale: Standard currency codes ensure proper financial processing.*
7. **Tax ID format**: supplier_tax_id and buyer_tax_id must match pattern (digits with optional hyphens). *Rationale: Tax ID format validation prevents data entry errors.*

### Business Logic Checks
8. **Date consistency**: due_date must be >= invoice_date. *Rationale: Due dates cannot precede invoice dates in valid business transactions.*
9. **Amount consistency**: total_amount must equal subtotal + tax_amount (within 0.01 tolerance). *Rationale: Invoice totals must mathematically reconcile to prevent accounting errors.*
10. **Line item totals**: Sum of line_item.line_total must equal subtotal (within 0.01 tolerance). *Rationale: Line item aggregation must match invoice subtotal for accuracy.*

### Anomaly/Duplicate Checks
11. **Duplicate invoice number**: invoice_number must be unique within supplier_name within last 12 months. *Rationale: Duplicate invoice numbers indicate potential duplicate payments or data errors.*
12. **Unusual amount**: total_amount > 3 standard deviations from supplier's historical average triggers review. *Rationale: Statistical outliers may indicate errors or fraud.*
13. **Future-dated invoice**: invoice_date cannot be > 7 days in the future. *Rationale: Future-dated invoices beyond reasonable buffer suggest data extraction errors.*

### Sanity Checks
14. **Positive amounts**: All monetary fields must be >= 0. *Rationale: Negative amounts require special handling and should be flagged.*
15. **Reasonable quantity**: line_item.quantity must be > 0 and < 1,000,000. *Rationale: Extreme quantities likely indicate extraction errors.*
16. **Valid date range**: invoice_date must be within last 5 years and not > today. *Rationale: Out-of-range dates indicate extraction or system errors.*

## Field Requirements

**Required**: invoice_number, invoice_date, supplier_name, buyer_name, total_amount, line_items (non-empty)

**Optional**: due_date, supplier_address, supplier_tax_id, buyer_address, buyer_tax_id, currency (defaults to "USD"), subtotal, tax_amount, payment_terms

**Internal invoice_id fallback**: If invoice_id is missing, generate as: `{supplier_name}_{invoice_number}_{invoice_date}` (normalized: uppercase, alphanumeric only, spaces→underscores). Example: `ACME_CORP_INV-2024-001234_2024-03-15`

