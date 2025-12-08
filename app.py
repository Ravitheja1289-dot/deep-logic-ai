import streamlit as st
import requests
import io
import json
import html
import os
from typing import List, Dict, Any

import tempfile
from pathlib import Path

# Default API URL (change in sidebar if your backend is hosted elsewhere)
# You can also set an env var STREAMLIT_API_URL in deployment to override.
DEFAULT_API_URL = os.getenv("STREAMLIT_API_URL", "http://localhost:8000")


from invoice_qc.extractor import extract_invoice
from invoice_qc.validator import validate_batch

# Default to local mode for easier deployment (no separate backend needed)
DEFAULT_API_URL = "" 

def process_files_locally(files: List[st.runtime.uploaded_file_manager.UploadedFile]) -> Dict[str, Any]:
    """Process files directly using imported modules (serverless mode)."""
    extracted_invoices = []
    
    for file in files:
        # Create temp file
        suffix = Path(file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            temp_file.write(file.getvalue())
            
        try:
            # Extract
            invoice_data = extract_invoice(temp_path)
            extracted_invoices.append(invoice_data)
        except Exception as e:
            extracted_invoices.append({
                'source_file': file.name,
                'error': f"Extraction failed: {str(e)}"
            })
        finally:
            # Cleanup
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
                
    # Validate
    valid_invoices = [inv for inv in extracted_invoices if 'error' not in inv]
    if valid_invoices:
        validation_result = validate_batch(valid_invoices)
    else:
        validation_result = {
            'per_invoice': [],
            'summary': {
                'total_invoices': 0, 'valid_count': 0, 'invalid_count': 0, 
                'error_counts': {}, 'duplicate_groups': 0
            }
        }
        
    return {
        'extracted': extracted_invoices,
        'validation': validation_result
    }

def process_json_locally(json_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process JSON directly using imported modules."""
    return validate_batch(json_data)


def send_files_to_api(files: List[st.runtime.uploaded_file_manager.UploadedFile], api_url: str, timeout: int = 60) -> Dict[str, Any]:
    if not files:
        raise ValueError("No files to send")

    endpoint = api_url.rstrip("/") + "/extract-and-validate-pdfs"
    multipart = []
    for f in files:
        # read bytes from Streamlit uploaded file
        content = f.read()
        # requests accepts bytes as file content
        multipart.append(
            ("files", (f.name, content, "application/pdf"))
        )

    resp = requests.post(endpoint, files=multipart, timeout=timeout)
    resp.raise_for_status()
    resp = requests.post(endpoint, files=multipart, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def send_json_to_api(json_data: List[Dict[str, Any]], api_url: str, timeout: int = 60) -> Dict[str, Any]:
    endpoint = api_url.rstrip("/") + "/validate-json"
    resp = requests.post(endpoint, json=json_data, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def render_summary(summary: Dict[str, Any]):
    """
    Render a compact summary box with totals.
    Expects keys: total_invoices, valid_count, invalid_count
    """
    total = summary.get("total_invoices", 0)
    valid = summary.get("valid_count", 0)
    invalid = summary.get("invalid_count", 0)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total invoices", total)
    c2.metric("Valid invoices", valid, delta=f"{int((valid/total*100) if total else 0)}%")
    c3.metric("Invalid invoices", invalid, delta=f"{int((invalid/total*100) if total else 0)}%")

    # Also show top error counts if available
    error_counts = summary.get("error_counts") or {}
    if error_counts:
        with st.expander("Top errors"):
            # show up to 10
            sorted_err = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            for e, cnt in sorted_err:
                st.write(f"- {e}: {cnt}")


# Removed _badge_html function - using emoji instead for better compatibility


def render_invoice_table(per_invoice: List[Dict[str, Any]], show_only_invalid: bool = False):
    """
    Render a table of invoices with colored badges for validity and comma-separated errors.
    Also renders an expander for detailed invoice info (line_items, raw_text).
    """
    if not per_invoice:
        st.info("No invoices to display.")
        return

    # Filter if requested
    if show_only_invalid:
        displayed = [inv for inv in per_invoice if not inv.get("is_valid", False)]
    else:
        displayed = per_invoice

    # Build table data for Streamlit
    table_data = []
    for inv in displayed:
        invoice_id = inv.get("invoice_id") or inv.get("invoice_number") or inv.get("source_file") or "—"
        is_valid = bool(inv.get("is_valid"))
        errors = inv.get("errors") or []
        errors_str = ", ".join(errors) if errors else "—"
        
        # Use emoji for status instead of HTML badge
        status = "✅ Valid" if is_valid else "❌ Invalid"
        
        table_data.append({
            "Invoice ID": invoice_id,
            "Status": status,
            "Errors": errors_str
        })
    
    # Display using Streamlit's native table
    if table_data:
        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Invoice ID": st.column_config.TextColumn("Invoice ID", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Errors": st.column_config.TextColumn("Errors", width="large")
            }
        )

    # Detailed expanders per invoice (respecting filter)
    for inv in displayed:
        invoice_id = inv.get("invoice_id") or inv.get("invoice_number") or inv.get("source_file") or "—"
        with st.expander(f"Details: {invoice_id}"):
            st.write("Status:", "✅ Valid" if inv.get("is_valid") else "❌ Invalid")
            st.write("Errors:")
            if inv.get("errors"):
                for e in inv.get("errors"):
                    st.write(f"- {e}")
            else:
                st.write("No errors found.")

            line_items = inv.get("line_items") or inv.get("extracted_line_items")
            if line_items:
                st.write("Line items:")
                try:
                    st.table(line_items)
                except Exception:
                    st.write(line_items)

            # Show extracted fields
            st.markdown("**Extracted Fields:**")
            extracted_data = {k: v for k, v in inv.items() if k not in ['errors', 'is_valid', 'invoice_id', 'line_items', 'raw_text', 'extracted_line_items']}
            if extracted_data:
                # Prepare data for table
                table_rows = []
                for key, value in extracted_data.items():
                    display_key = key.replace('_', ' ').title()
                    display_value = value if value is not None else "—"
                    table_rows.append({"Field": display_key, "Value": display_value})
                
                st.dataframe(
                    table_rows,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Field": st.column_config.TextColumn("Field", width="medium"),
                        "Value": st.column_config.TextColumn("Value", width="large")
                    }
                )
            else:
                st.info("No extracted fields available.")
            
            raw_text = inv.get("raw_text")
            if raw_text:
                st.write("**Raw Extracted Text:**")
                st.text_area("Raw text", raw_text, height=200, key=f"raw_text_{invoice_id}")
            else:
                st.warning("No raw text available. The PDF might be image-based or text extraction failed.")


def main():
    st.set_page_config(page_title="Invoice QC Console", layout="wide")
    st.title("Invoice QC Console")
    
    # Initialize response_data
    response_data = None

    # Sidebar: Backend configuration
    st.sidebar.header("Configuration")
    st.sidebar.info("Running in **Standalone Mode**. \nNo external backend required.")
    st.sidebar.markdown("---")
    st.sidebar.write("Usage:")
    st.sidebar.markdown("1. Upload PDF invoices\n2. Click **Extract & Validate**\n3. Review results")

    # Tabs for input method
    tab1, tab2 = st.tabs(["Upload PDF", "Paste JSON"])

    with tab1:
        # File uploader
        uploaded_files = st.file_uploader("Upload invoices", type=["pdf"], accept_multiple_files=True)

        col_left, col_right = st.columns([3, 1])
        with col_left:
            st.write("Select files and click the button to extract and validate.")
        with col_right:
            st.write("")  # spacer

        # Controls row
        btn_col1, btn_col2 = st.columns([1, 3])
        with btn_col1:
            extract_btn = st.button("Extract & Validate")
        with btn_col2:
            show_only_invalid = st.checkbox("Show only invalid invoices", value=False)

        if extract_btn:
            if not uploaded_files:
                st.warning("Please upload one or more PDF files before clicking Extract & Validate.")
            else:
                try:
                    with st.spinner("Processing files locally..."):
                        response_data = process_files_locally(uploaded_files)
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    with tab2:
        st.write("Paste a list of invoice JSON objects to validate them against the schema rules.")
        json_input = st.text_area("JSON / List of Invoices", height=300, help="e.g. [{'invoice_number': 'INV-1', ...}]")
        
        btn_col_json1, btn_col_json2 = st.columns([1, 3])
        with btn_col_json1:
            validate_json_btn = st.button("Validate JSON")
        with btn_col_json2:
            show_only_invalid_json = st.checkbox("Show only invalid (JSON)", value=False)

        if validate_json_btn:
            if not json_input.strip():
                st.warning("Please paste some JSON.")
            else:
                try:
                    parsed_input = json.loads(json_input)
                    if isinstance(parsed_input, dict):
                        parsed_input = [parsed_input]
                    if not isinstance(parsed_input, list):
                        st.error("Input must be a JSON object or a list of objects.")
                    else:
                        with st.spinner("Validating JSON locally..."):
                            api_resp = process_json_locally(parsed_input)
                            
                            # Normalize response
                            response_data = {
                                "extracted": parsed_input,
                                "validation": api_resp
                            }
                            # Update filter checkbox state for this view
                            show_only_invalid = show_only_invalid_json
                except json.JSONDecodeError:
                    st.error("Invalid JSON format.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    # If we have response data (either from this run or a previous run), render it
    if response_data:
        # Expecting: { "extracted": [...], "validation": { "summary": {...}, "per_invoice": [...] } }
        validation = response_data.get("validation") or {}
        extracted = response_data.get("extracted") or []
        per_invoice = validation.get("per_invoice") or []
        summary = validation.get("summary") or {}
        
        # Merge extracted invoice data with validation results
        # The validation results only have invoice_id, is_valid, and errors
        # We need to merge in the actual extracted fields
        merged_invoices = []
        for idx, val_result in enumerate(per_invoice):
            # Find corresponding extracted invoice
            extracted_inv = extracted[idx] if idx < len(extracted) else {}
            # Merge validation results with extracted data
            merged = {**extracted_inv, **val_result}
            merged_invoices.append(merged)

        st.subheader("Summary")
        render_summary(summary)

        st.subheader("Invoices")
        render_invoice_table(merged_invoices, show_only_invalid=show_only_invalid)

        # Option to download full report JSON
        st.download_button(
            label="Download Full Report (JSON)",
            data=json.dumps(response_data, indent=2),
            file_name="invoice_qc_report.json",
            mime="application/json"
        )

    # Helpful footer / troubleshooting
    st.markdown("---")
    st.markdown("If you encounter issues, check the request logs.")


if __name__ == "__main__":
    main()
