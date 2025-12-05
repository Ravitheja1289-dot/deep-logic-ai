"""
Utility helpers for invoice QC package.

Provides `normalize_invoice` which converts extractor output into the
canonical key names expected by the validator.
"""
from typing import Dict, Any


def normalize_invoice(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Return a new dict with canonical keys used across extractor/validator.

    - Ensures both `seller_name` and `supplier_name` exist (same value).
    - Ensures both `net_total` and `subtotal` exist.
    - Ensures both `gross_total` and `total_amount` exist.
    - Leaves `line_items` intact.
    """
    out: Dict[str, Any] = {}

    # Identity fields
    out['invoice_number'] = raw.get('invoice_number') or raw.get('invoice_id')
    out['invoice_date'] = raw.get('invoice_date')
    out['due_date'] = raw.get('due_date')

    # Names: provide both keys the validator might look for
    seller = raw.get('seller_name') or raw.get('supplier_name') or raw.get('seller')
    out['seller_name'] = seller
    out['supplier_name'] = seller

    buyer = raw.get('buyer_name') or raw.get('buyer')
    out['buyer_name'] = buyer

    # Tax IDs (both naming variants)
    out['supplier_tax_id'] = raw.get('supplier_tax_id') or raw.get('seller_tax_id')
    out['seller_tax_id'] = out['supplier_tax_id']
    out['buyer_tax_id'] = raw.get('buyer_tax_id')

    # Currency
    out['currency'] = raw.get('currency')

    # Amounts - ensure both naming conventions are present
    net = raw.get('net_total') or raw.get('subtotal') or raw.get('net')
    out['net_total'] = net
    out['subtotal'] = net

    tax = raw.get('tax_amount') or raw.get('tax')
    out['tax_amount'] = tax

    gross = raw.get('gross_total') or raw.get('total_amount') or raw.get('amount_due')
    out['gross_total'] = gross
    out['total_amount'] = gross

    # Line items + raw text + source file
    out['line_items'] = raw.get('line_items') or []
    out['raw_text'] = raw.get('raw_text')
    out['source_file'] = raw.get('source_file')

    # Keep any invoice_id if already present
    if raw.get('invoice_id'):
        out['invoice_id'] = raw.get('invoice_id')

    return out
