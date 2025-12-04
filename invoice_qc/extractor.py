"""
PDF invoice extraction module using pdfplumber.

Limitations: This module handles text-based PDFs only. Scanned images or
image-based PDFs require OCR preprocessing and are not supported.
"""

import re
from pathlib import Path
from typing import Optional, Dict, List, Any

import pdfplumber


def extract_text_from_pdf(path: str) -> str:
    """
    Extract all text content from a PDF file.

    Args:
        path: File path to the PDF file.

    Returns:
        Concatenated text from all pages of the PDF.
    """
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def _normalize_amount(text: str) -> Optional[float]:
    """
    Convert a string representation of currency to a float.

    Handles common currency formats: removes currency symbols, commas,
    and whitespace, then parses to float.

    Args:
        text: String containing a monetary amount.

    Returns:
        Float value of the amount, or None if parsing fails.
    """
    if not text:
        return None
    
    # Remove currency symbols, commas, whitespace
    cleaned = re.sub(r'[^\d.\-+]', '', text.strip())
    
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_invoice_number(text: str) -> Optional[str]:
    """Extract invoice number using common patterns."""
    patterns = [
        r'(?:invoice|inv)[\s#:]*([A-Z0-9\-]+)',
        r'invoice\s+number[\s:]+([A-Z0-9\-]+)',
        r'inv[\s#:]*([A-Z0-9\-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_date(text: str, label: str) -> Optional[str]:
    """Extract date field (invoice_date or due_date) using common patterns."""
    patterns = [
        rf'{label}[\s:]+(\d{{1,2}}[/\-]\d{{1,2}}[/\-]\d{{2,4}})',
        rf'{label}[\s:]+(\d{{4}}[/\-]\d{{1,2}}[/\-]\d{{1,2}})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            # Normalize to YYYY-MM-DD format if possible
            return _normalize_date(date_str)
    return None


def _normalize_date(date_str: str) -> Optional[str]:
    """Normalize date string to YYYY-MM-DD format."""
    # Try MM/DD/YYYY or YYYY-MM-DD patterns
    patterns = [
        (r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})', lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"),
        (r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})', lambda m: _normalize_short_date(m)),
    ]
    
    for pattern, formatter in patterns:
        match = re.match(pattern, date_str)
        if match:
            try:
                return formatter(match)
            except:
                continue
    return date_str  # Return as-is if normalization fails


def _normalize_short_date(match) -> str:
    """Normalize MM/DD/YYYY format to YYYY-MM-DD."""
    month, day, year = match.groups()
    if len(year) == 2:
        year = f"20{year}" if int(year) < 50 else f"19{year}"
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def _extract_name(text: str, label: str) -> Optional[str]:
    """Extract seller or buyer name using common patterns."""
    patterns = [
        rf'{label}[\s:]+([A-Z][A-Za-z\s&.,]+?)(?:\n|$)',
        rf'{label}[\s:]+([A-Z][A-Za-z\s&.,]+?)(?:\n|invoice|total|amount)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            # Clean up common artifacts
            name = re.sub(r'\s+', ' ', name)
            if len(name) > 2 and len(name) < 200:
                return name
    return None


def _extract_currency(text: str) -> Optional[str]:
    """Extract currency code or symbol."""
    # Look for ISO currency codes
    currency_match = re.search(r'\b(USD|EUR|GBP|INR|JPY|CAD|AUD)\b', text, re.IGNORECASE)
    if currency_match:
        return currency_match.group(1).upper()
    
    # Look for currency symbols
    if '$' in text and 'USD' not in text.upper():
        return 'USD'
    if '€' in text or 'EUR' in text.upper():
        return 'EUR'
    if '£' in text or 'GBP' in text.upper():
        return 'GBP'
    
    return None


def _extract_amount(text: str, label: str) -> Optional[float]:
    """Extract monetary amount by label."""
    patterns = [
        rf'{label}[\s:]*\$?\s*([\d,]+\.?\d*)',
        rf'{label}[\s:]*([\d,]+\.?\d*)\s*(?:USD|EUR|GBP)?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _normalize_amount(match.group(1))
    return None


def _extract_line_items(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract line items from PDF tables using pdfplumber.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of line item dictionaries with description, quantity, unit_price, line_total.
    """
    line_items = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                # Try to identify header row
                header_row = 0
                for i, row in enumerate(table[:3]):
                    if any(keyword in str(row).upper() for keyword in ['DESC', 'ITEM', 'QTY', 'PRICE', 'AMOUNT', 'TOTAL']):
                        header_row = i
                        break
                
                # Extract data rows
                for row in table[header_row + 1:]:
                    if not row or len(row) < 3:
                        continue
                    
                    # Try to extract meaningful data
                    row_str = ' '.join(str(cell) if cell else '' for cell in row)
                    if not row_str.strip() or 'total' in row_str.lower() or 'subtotal' in row_str.lower():
                        continue
                    
                    # Simple extraction: assume columns are description, quantity, price, total
                    description = str(row[0]).strip() if len(row) > 0 and row[0] else None
                    quantity = _normalize_amount(str(row[1])) if len(row) > 1 and row[1] else None
                    unit_price = _normalize_amount(str(row[2])) if len(row) > 2 and row[2] else None
                    line_total = _normalize_amount(str(row[3])) if len(row) > 3 and row[3] else None
                    
                    if description and (quantity or unit_price or line_total):
                        line_items.append({
                            'description': description,
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'line_total': line_total,
                        })
    
    return line_items


def extract_invoice(path: str) -> Dict[str, Any]:
    """
    Extract invoice data from a PDF file.

    Uses regex heuristics to extract invoice fields from text and pdfplumber
    tables for line items.

    Args:
        path: File path to the PDF invoice.

    Returns:
        Dictionary containing extracted invoice fields. Missing fields are None.
        Includes: invoice_number, invoice_date, due_date, seller_name, buyer_name,
        currency, net_total, tax_amount, gross_total, line_items, raw_text, source_file.
    """
    raw_text = extract_text_from_pdf(path)
    source_file = str(Path(path).name)
    
    invoice_data = {
        'invoice_number': _extract_invoice_number(raw_text),
        'invoice_date': _extract_date(raw_text, 'invoice date'),
        'due_date': _extract_date(raw_text, 'due date'),
        'seller_name': _extract_name(raw_text, 'seller') or _extract_name(raw_text, 'from') or _extract_name(raw_text, 'supplier'),
        'buyer_name': _extract_name(raw_text, 'buyer') or _extract_name(raw_text, 'to') or _extract_name(raw_text, 'bill to'),
        'currency': _extract_currency(raw_text),
        'net_total': _extract_amount(raw_text, 'subtotal') or _extract_amount(raw_text, 'net total') or _extract_amount(raw_text, 'total before tax'),
        'tax_amount': _extract_amount(raw_text, 'tax') or _extract_amount(raw_text, 'vat') or _extract_amount(raw_text, 'gst'),
        'gross_total': _extract_amount(raw_text, 'total') or _extract_amount(raw_text, 'grand total') or _extract_amount(raw_text, 'amount due'),
        'line_items': _extract_line_items(path),
        'raw_text': raw_text,
        'source_file': source_file,
    }
    
    return invoice_data

