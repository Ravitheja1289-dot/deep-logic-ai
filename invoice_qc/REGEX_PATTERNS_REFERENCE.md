# Robust Regex Patterns for Invoice Extraction

## 1. Invoice Number

**Pattern:**
```python
INVOICE_NUMBER_PATTERN = re.compile(
    r'(?:invoice\s*(?:number|no|#|num)?|inv\.?)\s*[:#]?\s*(?P<invoice_number>[A-Z0-9\-/]+)',
    re.IGNORECASE
)
```

**Handles variants:**
- "Invoice No: INV-2024-001"
- "Invoice # 12345"
- "Invoice Number: INV/2024/001"
- "INV-2024-001234"

**Example code:**
```python
import re

pattern = re.compile(
    r'(?:invoice\s*(?:number|no|#|num)?|inv\.?)\s*[:#]?\s*(?P<invoice_number>[A-Z0-9\-/]+)',
    re.IGNORECASE
)

match = pattern.search(text)
invoice_number = match.group('invoice_number') if match else None
```

---

## 2. Invoice Date

**Pattern:**
```python
INVOICE_DATE_PATTERN = re.compile(
    r'(?:invoice\s+)?date\s*[:]?\s*(?P<invoice_date>\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',
    re.IGNORECASE
)
```

**Handles variants:**
- "Date: 03/15/2024"
- "Invoice Date: 2024-03-15"
- "Date 15-03-2024"
- "Date: 3/15/24"

**Example code:**
```python
pattern = re.compile(
    r'(?:invoice\s+)?date\s*[:]?\s*(?P<invoice_date>\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',
    re.IGNORECASE
)

match = pattern.search(text)
invoice_date = match.group('invoice_date') if match else None
```

---

## 3. Due Date

**Pattern:**
```python
DUE_DATE_PATTERN = re.compile(
    r'(?:due\s+date|payment\s+due|due\s+by|due)\s*[:]?\s*(?P<due_date>\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',
    re.IGNORECASE
)
```

**Handles variants:**
- "Due Date: 04/14/2024"
- "Payment Due: 2024-04-14"
- "Due: 14-04-2024"
- "Due By: 4/14/24"

**Example code:**
```python
pattern = re.compile(
    r'(?:due\s+date|payment\s+due|due\s+by|due)\s*[:]?\s*(?P<due_date>\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',
    re.IGNORECASE
)

match = pattern.search(text)
due_date = match.group('due_date') if match else None
```

---

## 4. Currency

**Pattern:**
```python
CURRENCY_PATTERN = re.compile(
    r'(?:currency\s*[:]?\s*)?(?P<currency>\b(?:USD|EUR|GBP|INR|JPY|CAD|AUD|CHF|CNY|SGD|HKD|NZD|MXN|BRL|ZAR)\b|[$€£¥₹])',
    re.IGNORECASE
)
```

**Handles variants:**
- "Currency: USD"
- "USD"
- "$" (maps to USD)
- "€" (maps to EUR)
- "GBP"

**Example code:**
```python
pattern = re.compile(
    r'(?:currency\s*[:]?\s*)?(?P<currency>\b(?:USD|EUR|GBP|INR|JPY|CAD|AUD|CHF|CNY|SGD|HKD|NZD|MXN|BRL|ZAR)\b|[$€£¥₹])',
    re.IGNORECASE
)

match = pattern.search(text)
if match:
    currency = match.group('currency').upper()
    symbol_map = {'$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR'}
    currency = symbol_map.get(currency, currency)
```

---

## 5. Net Total (Subtotal)

**Pattern:**
```python
NET_TOTAL_PATTERN = re.compile(
    r'(?:subtotal|net\s+total|total\s+before\s+tax|amount\s+before\s+tax)\s*[:]?\s*(?P<net_total>[$€£¥₹]?\s*[\d,]+\.?\d*)',
    re.IGNORECASE
)
```

**Handles variants:**
- "Subtotal: $15,000.00"
- "Net Total: 15000.00"
- "Total Before Tax: 15,000"
- "Subtotal: €12,500.50"

**Example code:**
```python
pattern = re.compile(
    r'(?:subtotal|net\s+total|total\s+before\s+tax|amount\s+before\s+tax)\s*[:]?\s*(?P<net_total>[$€£¥₹]?\s*[\d,]+\.?\d*)',
    re.IGNORECASE
)

match = pattern.search(text)
if match:
    amount_str = re.sub(r'[^\d.,]', '', match.group('net_total'))
    amount_str = amount_str.replace(',', '')  # Remove thousand separators
    net_total = float(amount_str)
```

---

## 6. Tax Amount

**Pattern:**
```python
TAX_AMOUNT_PATTERN = re.compile(
    r'(?:(?:tax|vat|gst|sales\s+tax)\s*(?:amount|amt)?|tax\s+total)\s*[:]?\s*(?P<tax_amount>[$€£¥₹]?\s*[\d,]+\.?\d*)',
    re.IGNORECASE
)
```

**Handles variants:**
- "Tax: $1,200.00"
- "VAT: 1200.00"
- "GST Amount: 1,200.00"
- "Sales Tax: $1,200"

**Example code:**
```python
pattern = re.compile(
    r'(?:(?:tax|vat|gst|sales\s+tax)\s*(?:amount|amt)?|tax\s+total)\s*[:]?\s*(?P<tax_amount>[$€£¥₹]?\s*[\d,]+\.?\d*)',
    re.IGNORECASE
)

match = pattern.search(text)
if match:
    amount_str = re.sub(r'[^\d.,]', '', match.group('tax_amount'))
    amount_str = amount_str.replace(',', '')
    tax_amount = float(amount_str)
```

---

## 7. Gross Total (Total Amount)

**Pattern:**
```python
GROSS_TOTAL_PATTERN = re.compile(
    r'(?:grand\s+total|total\s+amount|amount\s+due|total\s+due|final\s+total|^total\s*[:]?)\s*(?P<gross_total>[$€£¥₹]?\s*[\d,]+\.?\d*)',
    re.IGNORECASE | re.MULTILINE
)
```

**Handles variants:**
- "Total: $16,200.00"
- "Grand Total: 16200.00"
- "Amount Due: $16,200.00"
- "Total Amount: €15,000.50"

**Example code:**
```python
pattern = re.compile(
    r'(?:grand\s+total|total\s+amount|amount\s+due|total\s+due|final\s+total|^total\s*[:]?)\s*(?P<gross_total>[$€£¥₹]?\s*[\d,]+\.?\d*)',
    re.IGNORECASE | re.MULTILINE
)

match = pattern.search(text)
if match:
    amount_str = re.sub(r'[^\d.,]', '', match.group('gross_total'))
    amount_str = amount_str.replace(',', '')
    gross_total = float(amount_str)
```

---

## Notes

- All patterns use **named groups** (`?P<field_name>`) for easy extraction
- Patterns are case-insensitive (`re.IGNORECASE`)
- Amount patterns handle commas as thousand separators (e.g., "15,000.00")
- Currency symbols are automatically mapped to ISO codes
- Date patterns accept both MM/DD/YYYY and YYYY-MM-DD formats


