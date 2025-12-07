import streamlit as st
import requests
import io
import json
import html
import os
from typing import List, Dict, Any

# Default API URL (change in sidebar if your backend is hosted elsewhere)
# You can also set an env var STREAMLIT_API_URL in deployment to override.
DEFAULT_API_URL = os.getenv("STREAMLIT_API_URL", "http://localhost:8000")


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
                # Display as a clean key-value table
                for key, value in extracted_data.items():
                    if value is not None:
                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                    else:
                        st.write(f"**{key.replace('_', ' ').title()}:** —")
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

    # Sidebar: API configuration
    st.sidebar.header("Backend")
    api_url = st.sidebar.text_input(
        "API base URL",
        value=DEFAULT_API_URL,
        help="For deployed Streamlit, set this to your public FastAPI URL (not localhost).",
    )
    st.sidebar.write("Endpoint used: ", f"`{api_url.rstrip('/')}/extract-and-validate-pdfs`")
    if "localhost" in api_url:
        st.sidebar.warning(
            "Deployed Streamlit cannot reach localhost. Set this to your public FastAPI URL.",
            icon="⚠️",
        )

    # Quick health check
    if st.sidebar.button("Check API health"):
        try:
            resp = requests.get(api_url.rstrip("/") + "/health", timeout=10)
            resp.raise_for_status()
            st.sidebar.success(f"API OK: {resp.json()}")
        except Exception as e:
            st.sidebar.error(f"API health check failed: {e}")
    st.sidebar.markdown("---")
    st.sidebar.write("Usage:")
    st.sidebar.markdown("1. Upload PDF invoices\n2. Click **Extract & Validate**\n3. Review results")

    # File uploader
    uploaded_files = st.file_uploader("Upload invoices", type=["pdf"], accept_multiple_files=True)

    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.write("Select files and click the button to send to the backend for extraction and validation.")
    with col_right:
        st.write("")  # spacer

    # Controls row
    btn_col1, btn_col2 = st.columns([1, 3])
    with btn_col1:
        extract_btn = st.button("Extract & Validate")
    with btn_col2:
        show_only_invalid = st.checkbox("Show only invalid invoices", value=False)

    response_data = None

    if extract_btn:
        if not uploaded_files:
            st.warning("Please upload one or more PDF files before clicking Extract & Validate.")
        else:
            try:
                with st.spinner("Uploading files and requesting extraction/validation..."):
                    response_data = send_files_to_api(uploaded_files, api_url)
            except requests.RequestException as e:
                st.error(f"API request failed: {str(e)}")
                try:
                    if hasattr(e, "response") and e.response is not None:
                        st.json(e.response.text)
                except Exception:
                    pass
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
    st.markdown("If the API is unreachable, ensure your FastAPI server is running and the URL in the sidebar is correct.")
    st.markdown("Example local URL: `http://localhost:8000`")


if __name__ == "__main__":
    main()
