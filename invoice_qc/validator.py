"""
Invoice validation module with deterministic error tokens.

Provides single invoice and batch validation with clear error reporting.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from dateutil import parser as date_parser

# Numeric tolerance factor: 0.5%
TOLERANCE_FACTOR = 0.005

# Valid currency codes (expanded list to match extractor patterns)
VALID_CURRENCIES = {
    'EUR', 'USD', 'INR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY',
    'SGD', 'HKD', 'NZD', 'MXN', 'BRL', 'ZAR'
}


def _generate_invoice_id(invoice: Dict[str, Any]) -> str:
    """
    Generate internal invoice_id fallback if missing.
    
    Format: {supplier_name}_{invoice_number}_{invoice_date}
    Normalized: uppercase, alphanumeric only, spaces->underscores
    """
    supplier = invoice.get('supplier_name') or invoice.get('seller_name') or 'UNKNOWN'
    invoice_num = invoice.get('invoice_number') or 'UNKNOWN'
    invoice_date = invoice.get('invoice_date') or 'UNKNOWN'
    
    # Normalize: uppercase, alphanumeric and hyphens/underscores only, spaces->underscores
    supplier_norm = ''.join(c if c.isalnum() or c in '-_' else '_' for c in supplier.upper())
    supplier_norm = '_'.join(supplier_norm.split())
    
    return f"{supplier_norm}_{invoice_num}_{invoice_date}"


def _parse_date(date_str: Any) -> Optional[datetime]:
    """Parse date string using dateutil.parser, return None if unparsable."""
    if not date_str:
        return None
    
    try:
        return date_parser.parse(str(date_str), fuzzy=False)
    except (ValueError, TypeError, OverflowError):
        return None


def _is_within_tolerance(value1: float, value2: float, tolerance: float = TOLERANCE_FACTOR) -> bool:
    """
    Check if two numeric values are within tolerance.
    
    Uses relative tolerance: |value1 - value2| <= max(|value1|, |value2|) * tolerance
    """
    if value1 is None or value2 is None:
        return False
    
    diff = abs(value1 - value2)
    max_val = max(abs(value1), abs(value2))
    
    # Handle zero case
    if max_val == 0:
        return diff == 0
    
    return diff <= max_val * tolerance


def _validate_missing_fields(invoice: Dict[str, Any]) -> List[str]:
    """Check for missing required fields."""
    errors = []
    
    if not invoice.get('invoice_number'):
        errors.append('missing_field:invoice_number')
    if not invoice.get('invoice_date'):
        errors.append('missing_field:invoice_date')
    if not invoice.get('seller_name') and not invoice.get('supplier_name'):
        errors.append('missing_field:seller_name')
    if not invoice.get('buyer_name'):
        errors.append('missing_field:buyer_name')
    
    return errors


def _validate_format(invoice: Dict[str, Any]) -> List[str]:
    """Validate field formats."""
    errors = []
    
    # Validate invoice_date format
    invoice_date = invoice.get('invoice_date')
    if invoice_date:
        parsed_date = _parse_date(invoice_date)
        if parsed_date is None:
            errors.append('invalid_format:invoice_date')
    
    return errors


def _validate_currency(invoice: Dict[str, Any]) -> List[str]:
    """Validate currency code."""
    errors = []
    
    currency = invoice.get('currency')
    if currency and currency.upper() not in VALID_CURRENCIES:
        errors.append('invalid_value:currency')
    
    return errors


def _validate_business_rules(invoice: Dict[str, Any]) -> List[str]:
    """Validate business logic rules."""
    errors = []
    
    # Get amounts (handle both naming conventions)
    net_total = invoice.get('net_total') or invoice.get('subtotal')
    tax_amount = invoice.get('tax_amount')
    gross_total = invoice.get('gross_total') or invoice.get('total_amount')
    
    # Rule: totals_mismatch (net + tax ≈ gross)
    if net_total is not None and tax_amount is not None and gross_total is not None:
        expected_gross = net_total + tax_amount
        if not _is_within_tolerance(gross_total, expected_gross):
            errors.append('business_rule:totals_mismatch')
    
    # Rule: linesum_mismatch (sum of line_items ≈ net_total)
    line_items = invoice.get('line_items', [])
    if line_items and net_total is not None:
        line_sum = 0.0
        for item in line_items:
            # Handle both naming conventions
            line_total = item.get('line_total') or item.get('amount') or 0.0
            if line_total:
                line_sum += float(line_total)
        
        if line_sum > 0 and not _is_within_tolerance(net_total, line_sum):
            errors.append('business_rule:linesum_mismatch')
    
    # Rule: due_before_invoice
    invoice_date = invoice.get('invoice_date')
    due_date = invoice.get('due_date')
    
    if invoice_date and due_date:
        parsed_invoice_date = _parse_date(invoice_date)
        parsed_due_date = _parse_date(due_date)
        
        if parsed_invoice_date and parsed_due_date:
            if parsed_due_date < parsed_invoice_date:
                errors.append('business_rule:due_before_invoice')
    
    return errors


def _validate_sanity_checks(invoice: Dict[str, Any]) -> List[str]:
    """Validate sanity checks."""
    errors = []
    
    # Rule: negative_gross
    gross_total = invoice.get('gross_total') or invoice.get('total_amount')
    if gross_total is not None and gross_total < 0:
        errors.append('sanity:negative_gross')
    
    return errors


def _detect_duplicates(invoices: List[Dict[str, Any]]) -> Dict[Tuple[str, str, str], List[int]]:
    """
    Detect duplicate invoices in batch.
    
    Returns dict mapping (invoice_number, supplier_tax_id, invoice_date) -> list of indices
    """
    seen = {}
    duplicates = {}
    
    for idx, invoice in enumerate(invoices):
        invoice_number = invoice.get('invoice_number')
        supplier_tax_id = invoice.get('supplier_tax_id') or invoice.get('seller_tax_id') or ''
        invoice_date = invoice.get('invoice_date') or ''
        
        if invoice_number:
            key = (str(invoice_number), str(supplier_tax_id), str(invoice_date))
            
            if key in seen:
                if key not in duplicates:
                    duplicates[key] = [seen[key]]
                duplicates[key].append(idx)
            else:
                seen[key] = idx
    
    return duplicates


def validate_invoice(invoice: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a single invoice.
    
    Args:
        invoice: Dictionary containing invoice data.
    
    Returns:
        Dictionary with keys:
        - invoice_id: Generated or existing invoice ID
        - is_valid: Boolean indicating if invoice passed all validations
        - errors: List of error token strings
    """
    errors = []
    
    # Generate invoice_id if missing
    invoice_id = invoice.get('invoice_id')
    if not invoice_id:
        invoice_id = _generate_invoice_id(invoice)
    
    # Run all validation checks
    errors.extend(_validate_missing_fields(invoice))
    errors.extend(_validate_format(invoice))
    errors.extend(_validate_currency(invoice))
    errors.extend(_validate_business_rules(invoice))
    errors.extend(_validate_sanity_checks(invoice))
    
    return {
        'invoice_id': invoice_id,
        'is_valid': len(errors) == 0,
        'errors': errors
    }


def validate_batch(invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a batch of invoices, including duplicate detection.
    
    Args:
        invoices: List of invoice dictionaries.
    
    Returns:
        Dictionary with keys:
        - per_invoice: List of validation results (same format as validate_invoice)
        - summary: Dictionary with aggregate statistics
    """
    per_invoice = []
    duplicate_map = _detect_duplicates(invoices)
    
    # Validate each invoice
    for idx, invoice in enumerate(invoices):
        result = validate_invoice(invoice)
        
        # Add duplicate error if this invoice is part of a duplicate set
        invoice_number = invoice.get('invoice_number')
        supplier_tax_id = invoice.get('supplier_tax_id') or invoice.get('seller_tax_id') or ''
        invoice_date = invoice.get('invoice_date') or ''
        
        if invoice_number:
            key = (str(invoice_number), str(supplier_tax_id), str(invoice_date))
            if key in duplicate_map and idx in duplicate_map[key]:
                result['errors'].append('anomaly:duplicate_invoice')
                result['is_valid'] = False
        
        per_invoice.append(result)
    
    # Build summary
    total = len(invoices)
    valid_count = sum(1 for r in per_invoice if r['is_valid'])
    invalid_count = total - valid_count
    
    # Count errors by type
    error_counts = {}
    for result in per_invoice:
        for error in result['errors']:
            error_counts[error] = error_counts.get(error, 0) + 1
    
    summary = {
        'total_invoices': total,
        'valid_count': valid_count,
        'invalid_count': invalid_count,
        'error_counts': error_counts,
        'duplicate_groups': len(duplicate_map)
    }
    
    return {
        'per_invoice': per_invoice,
        'summary': summary
    }


