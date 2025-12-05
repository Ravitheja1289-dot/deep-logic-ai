"""
Robust regex patterns for invoice field extraction with named groups.

These patterns handle common variants found in B2B invoices.
"""

import re
from typing import Optional
from datetime import datetime


# 1. INVOICE NUMBER
# Handles: "Invoice No:", "Invoice #", "INV-2024-001", "Invoice Number: INV-12345", "#12345", "No. 12345"
# Also handles German: "Bestellung AUFNR89493", "Rechnung Nr. 12345", "Auftrag 12345"
INVOICE_NUMBER_PATTERN = re.compile(
    r'(?:invoice\s*(?:number|no|#|num|num\.)?|inv\.?|^#|^no\.?|bestellung|rechnung\s*(?:nr|nummer)?|auftrag|aufnr)\s*[:#]?\s*(?P<invoice_number>[A-Z0-9\-/]+)',
    re.IGNORECASE | re.MULTILINE
)

def extract_invoice_number(text: str) -> Optional[str]:
    """Extract invoice number using robust pattern."""
    match = INVOICE_NUMBER_PATTERN.search(text)
    return match.group('invoice_number').strip() if match else None


# 2. INVOICE DATE
# Handles: "Date: 03/15/2024", "Invoice Date: 2024-03-15", "Date 15-Mar-2024", "Issued: 03/15/2024"
# Also handles German: "vom 18.08.2025" (DD.MM.YYYY format), "Datum: 18.08.2025"
INVOICE_DATE_PATTERN = re.compile(
    r'(?:invoice\s+)?(?:date|issued|issue\s+date|vom|datum)\s*[:]?\s*(?P<invoice_date>\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})',
    re.IGNORECASE
)

def extract_invoice_date(text: str) -> Optional[str]:
    """Extract invoice date using robust pattern and normalize to YYYY-MM-DD."""
    match = INVOICE_DATE_PATTERN.search(text)
    if match:
        date_str = match.group('invoice_date').strip()
        return _normalize_date_string(date_str)
    return None


# 3. DUE DATE
# Handles: "Due Date: 04/14/2024", "Payment Due: 2024-04-14", "Due: 14-Apr-2024"
DUE_DATE_PATTERN = re.compile(
    r'(?:due\s+date|payment\s+due|due\s+by|due)\s*[:]?\s*(?P<due_date>\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',
    re.IGNORECASE
)

def extract_due_date(text: str) -> Optional[str]:
    """Extract due date using robust pattern and normalize to YYYY-MM-DD."""
    match = DUE_DATE_PATTERN.search(text)
    if match:
        date_str = match.group('due_date').strip()
        return _normalize_date_string(date_str)
    return None


# 4. CURRENCY
# Handles: "USD", "Currency: EUR", "$", "€", "GBP"
CURRENCY_PATTERN = re.compile(
    r'(?:currency\s*[:]?\s*)?(?P<currency>\b(?:USD|EUR|GBP|INR|JPY|CAD|AUD|CHF|CNY|SGD|HKD|NZD|MXN|BRL|ZAR)\b|[$€£¥₹])',
    re.IGNORECASE
)

def extract_currency(text: str) -> Optional[str]:
    """Extract currency code or symbol."""
    match = CURRENCY_PATTERN.search(text)
    if match:
        currency = match.group('currency').upper()
        # Map symbols to codes
        symbol_map = {'$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR'}
        return symbol_map.get(currency, currency)
    return None


# 5. NET TOTAL (Subtotal)
# Handles: "Subtotal: $15,000.00", "Net Total: 15000.00", "Total Before Tax: 15,000"
# Also handles German: "Gesamtwert EUR 264,00" (comma as decimal separator)
NET_TOTAL_PATTERN = re.compile(
    r'(?:subtotal|net\s+total|total\s+before\s+tax|amount\s+before\s+tax|gesamtwert|nettobetrag|zwischensumme)\s*(?:EUR|USD|€|\$)?\s*[:]?\s*(?P<net_total>[$€£¥₹]?\s*[\d.,]+[.,]?\d*)',
    re.IGNORECASE
)

def extract_net_total(text: str) -> Optional[float]:
    """Extract net total (subtotal) amount."""
    match = NET_TOTAL_PATTERN.search(text)
    if match:
        amount_str = re.sub(r'[^\d.,]', '', match.group('net_total'))
        # Handle German format: comma as decimal separator (264,00)
        # Check if comma is likely decimal (if followed by 2 digits at end) or thousands separator
        if ',' in amount_str and '.' in amount_str:
            # Both present: determine which is decimal
            parts = amount_str.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Comma is decimal (e.g., "1.234,56")
                amount_str = amount_str.replace('.', '').replace(',', '.')
            else:
                # Period is decimal (e.g., "1,234.56")
                amount_str = amount_str.replace(',', '')
        elif ',' in amount_str:
            # Only comma: check if it's decimal (2 digits after) or thousands
            parts = amount_str.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Comma is decimal separator (German format)
                amount_str = amount_str.replace(',', '.')
            else:
                # Comma is thousands separator
                amount_str = amount_str.replace(',', '')
        else:
            # Only period or neither: period is decimal
            pass
        try:
            return float(amount_str)
        except ValueError:
            return None
    return None


# 6. TAX AMOUNT
# Handles: "Tax: $1,200.00", "VAT: 1200.00", "GST Amount: 1,200.00"
# Also handles German: "MwSt. 19,00% EUR 50,16" (MwSt = Mehrwertsteuer = VAT)
TAX_AMOUNT_PATTERN = re.compile(
    r'(?:(?:tax|vat|gst|sales\s+tax|mwst\.?|mehrwertsteuer)\s*(?:amount|amt)?|tax\s+total)\s*(?:\d+[,.]?\d*%)?\s*(?:EUR|USD|€|\$)?\s*[:]?\s*(?P<tax_amount>[$€£¥₹]?\s*[\d.,]+[.,]?\d*)',
    re.IGNORECASE
)

def extract_tax_amount(text: str) -> Optional[float]:
    """Extract tax/VAT/GST amount."""
    match = TAX_AMOUNT_PATTERN.search(text)
    if match:
        amount_str = re.sub(r'[^\d.,]', '', match.group('tax_amount'))
        # Handle German format: comma as decimal separator
        if ',' in amount_str and '.' in amount_str:
            parts = amount_str.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                amount_str = amount_str.replace('.', '').replace(',', '.')
            else:
                amount_str = amount_str.replace(',', '')
        elif ',' in amount_str:
            parts = amount_str.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                amount_str = amount_str.replace(',', '.')
            else:
                amount_str = amount_str.replace(',', '')
        try:
            return float(amount_str)
        except ValueError:
            return None
    return None


# 7. GROSS TOTAL (Total Amount)
# Handles: "Total: $16,200.00", "Grand Total: 16200.00", "Amount Due: $16,200.00"
# Also handles German: "Gesamtwert inkl. MwSt. EUR 314,16"
GROSS_TOTAL_PATTERN = re.compile(
    r'(?:grand\s+total|total\s+amount|amount\s+due|total\s+due|final\s+total|^total\s*[:]?|gesamtwert\s+(?:inkl\.?\s*)?(?:mwst\.?|inklusive)|endbetrag|rechnungsbetrag)\s*(?:EUR|USD|€|\$)?\s*(?P<gross_total>[$€£¥₹]?\s*[\d.,]+[.,]?\d*)',
    re.IGNORECASE | re.MULTILINE
)

def extract_gross_total(text: str) -> Optional[float]:
    """Extract gross total (final amount)."""
    match = GROSS_TOTAL_PATTERN.search(text)
    if match:
        amount_str = re.sub(r'[^\d.,]', '', match.group('gross_total'))
        # Handle German format: comma as decimal separator
        if ',' in amount_str and '.' in amount_str:
            parts = amount_str.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                amount_str = amount_str.replace('.', '').replace(',', '.')
            else:
                amount_str = amount_str.replace(',', '')
        elif ',' in amount_str:
            parts = amount_str.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                amount_str = amount_str.replace(',', '.')
            else:
                amount_str = amount_str.replace(',', '')
        try:
            return float(amount_str)
        except ValueError:
            return None
    return None


# 8. SELLER/SUPPLIER NAME
# Handles: "From:", "Seller:", "Supplier:", "Vendor:", "Bill From:", company name at top
# Also handles German: company name before "im Auftrag von"
SELLER_NAME_PATTERN = re.compile(
    r'(?:from|seller|supplier|vendor|bill\s+from|sold\s+by|^|im\s+auftrag\s+von)\s*[:]?\s*(?P<seller_name>[A-Z][A-Za-z0-9\s&.,\-()]+?)(?:\n|$|(?:\n.*?(?:to|buyer|bill\s+to|invoice|date|total|address|kundenanschrift|lieferbedingungen)))',
    re.IGNORECASE | re.MULTILINE | re.DOTALL
)

def extract_seller_name(text: str) -> Optional[str]:
    """Extract seller/supplier name using robust pattern."""
    lines = text.split('\n')
    
    # Special handling for German format: look for company name that appears after buyer info
    # Pattern: buyer name appears multiple times, then supplier name appears
    # Look for company names with country in parentheses (common format)
    for i, line in enumerate(lines[:20]):
        line = line.strip()
        # Look for company names with parentheses (often contains country)
        if '(' in line and ')' in line and re.match(r'^[A-Z]', line):
            # Check if it looks like a company name
            if 5 < len(line) < 100 and not re.match(r'^\d+', line):
                # Skip if it's clearly an address or other field
                if not any(word in line.upper() for word in ['KUNDENANSCHRIFT', 'ADRESSE', 'ADDRESS', 'FAX', 'TELEFON', 'PHONE']):
                    return line
    
    # Special handling for German format: look for company name before "im Auftrag von"
    auftrag_match = re.search(r'([A-Z][A-Za-z0-9\s&.,\-()]+?)\s+im\s+auftrag\s+von', text, re.IGNORECASE)
    if auftrag_match:
        name = auftrag_match.group(1).strip()
        # Skip page numbers and order numbers
        if (not re.match(r'^seite\s+\d+\s+von\s+\d+', name, re.IGNORECASE) and
            not re.match(r'^.*bestellung.*aufnr', name, re.IGNORECASE)):
            if 2 < len(name) < 200:
                return name
    
    # Try pattern-based extraction
    match = SELLER_NAME_PATTERN.search(text)
    if match:
        name = match.group('seller_name').strip()
        # Skip page numbers
        if re.match(r'^seite\s+\d+\s+von\s+\d+', name, re.IGNORECASE):
            # Try to find the next match
            matches = list(SELLER_NAME_PATTERN.finditer(text))
            for m in matches[1:]:  # Skip first match
                name = m.group('seller_name').strip()
                if not re.match(r'^seite\s+\d+\s+von\s+\d+', name, re.IGNORECASE):
                    break
        # Clean up: remove extra whitespace, limit length
        name = re.sub(r'\s+', ' ', name)
        # Remove common trailing artifacts
        name = re.sub(r'\s*[,;]\s*$', '', name)
        if 2 < len(name) < 200 and not re.match(r'^seite\s+\d+\s+von\s+\d+', name, re.IGNORECASE):
            return name
    
    # Fallback: try to find company name in first few lines (common invoice format)
    for line in lines[:15]:
        line = line.strip()
        # Skip page numbers and labels
        if re.match(r'^(seite\s+\d+\s+von\s+\d+|invoice|date|total|amount|from|to|bestellung|rechnung)', line, re.IGNORECASE):
            continue
        # Look for lines that look like company names (capitalized, reasonable length, not dates/numbers)
        if (len(line) > 3 and len(line) < 100 and 
            not re.match(r'^\d+[/\-\.]', line) and  # Not a date
            not re.match(r'^[#\$]', line) and  # Not starting with # or $
            re.match(r'^[A-Z]', line)):  # Starts with capital
            # Check if it contains typical company indicators
            if any(word in line.upper() for word in ['CORP', 'GMBH', 'AG', 'LTD', 'INC', 'LLC', 'SUPPLIES', 'EQUIP', 'DEUTSCHLAND']):
                return line
            # Or if it's a reasonable company name length and looks like a company
            if 5 < len(line) < 80 and '(' in line:  # Often has country in parentheses
                return line
            # Or if it's a reasonable company name
            if 8 < len(line) < 80:
                return line
    
    return None


# 9. BUYER NAME
# Handles: "To:", "Buyer:", "Bill To:", "Customer:", "Client:"
# Also handles German: "Kundenanschrift" (customer address), "Bitte liefern Sie an:" (please deliver to)
BUYER_NAME_PATTERN = re.compile(
    r'(?:to|buyer|bill\s+to|customer|client|sold\s+to|kundenanschrift|bitte\s+liefern\s+sie\s+an|lieferadresse)\s*[:]?\s*(?P<buyer_name>[A-Z][A-Za-z0-9\s&.,\-()]+?)(?:\n|$|(?:\n.*?(?:from|seller|supplier|invoice|date|total|bestellung|rechnung)))',
    re.IGNORECASE | re.MULTILINE | re.DOTALL
)

def extract_buyer_name(text: str) -> Optional[str]:
    """Extract buyer/customer name using robust pattern."""
    match = BUYER_NAME_PATTERN.search(text)
    if match:
        name = match.group('buyer_name').strip()
        # Clean up: remove extra whitespace, limit length
        name = re.sub(r'\s+', ' ', name)
        # Remove common trailing artifacts
        name = re.sub(r'\s*[,;]\s*$', '', name)
        if 2 < len(name) < 200:
            return name
    return None


def _normalize_date_string(date_str: str) -> Optional[str]:
    """Normalize date string to YYYY-MM-DD format."""
    if not date_str:
        return None
    
    # Clean up the date string
    date_str = date_str.strip()
    
    # Try common date formats (including German DD.MM.YYYY)
    formats = [
        '%Y-%m-%d',      # 2024-03-15
        '%m/%d/%Y',      # 03/15/2024
        '%d/%m/%Y',      # 15/03/2024
        '%Y/%m/%d',      # 2024/03/15
        '%m-%d-%Y',      # 03-15-2024
        '%d-%m-%Y',      # 15-03-2024
        '%m/%d/%y',      # 03/15/24
        '%d/%m/%y',      # 15/03/24
        '%m.%d.%Y',      # 03.15.2024
        '%d.%m.%Y',      # 18.08.2025 (German format)
        '%d.%m.%y',      # 18.08.25
        '%d %b %Y',      # 15 Mar 2024
        '%d %B %Y',      # 15 March 2024
        '%b %d, %Y',     # Mar 15, 2024
        '%B %d, %Y',     # March 15, 2024
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # If no format matches, try to parse with regex and guess format
    # Handle MM/DD/YYYY or DD/MM/YYYY ambiguity
    parts = re.split(r'[/\-\.]', date_str)
    if len(parts) == 3:
        try:
            # Try YYYY-MM-DD first
            if len(parts[0]) == 4:
                year, month, day = parts[0], parts[1], parts[2]
                dt = datetime(int(year), int(month), int(day))
                return dt.strftime('%Y-%m-%d')
            # Try MM/DD/YYYY (US format)
            elif len(parts[2]) == 4:
                month, day, year = parts[0], parts[1], parts[2]
                dt = datetime(int(year), int(month), int(day))
                return dt.strftime('%Y-%m-%d')
            # Try DD/MM/YYYY (European format)
            elif len(parts[0]) <= 2 and len(parts[1]) <= 2:
                day, month, year = parts[0], parts[1], parts[2]
                if len(year) == 2:
                    year = f"20{year}" if int(year) < 50 else f"19{year}"
                dt = datetime(int(year), int(month), int(day))
                return dt.strftime('%Y-%m-%d')
        except (ValueError, IndexError):
            pass
    
    # Return as-is if we can't normalize (validator will catch invalid format)
    return date_str


# Example usage with all patterns:
def extract_all_fields(text: str) -> dict:
    """Extract all invoice fields using the robust patterns."""
    return {
        'invoice_number': extract_invoice_number(text),
        'invoice_date': extract_invoice_date(text),
        'due_date': extract_due_date(text),
        'currency': extract_currency(text),
        'net_total': extract_net_total(text),
        'tax_amount': extract_tax_amount(text),
        'gross_total': extract_gross_total(text),
        'seller_name': extract_seller_name(text),
        'buyer_name': extract_buyer_name(text),
    }


