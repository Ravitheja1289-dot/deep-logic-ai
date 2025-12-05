import pytest

from invoice_qc import validator


def test_totals_mismatch_detected():
    invoice = {
        'invoice_number': 'INV-1',
        'invoice_date': '2024-01-01',
        'seller_name': 'Acme',
        'buyer_name': 'Buyer',
        'net_total': 100.0,
        'tax_amount': 10.0,
        'gross_total': 120.0,  # mismatch (should be ~110)
        'line_items': [{'line_total': 100.0}],
    }

    res = validator.validate_invoice(invoice)
    assert 'business_rule:totals_mismatch' in res['errors']


def test_duplicate_detection():
    invoices = [
        {'invoice_number': 'INV-2', 'supplier_tax_id': 'TAX1', 'invoice_date': '2024-01-01'},
        {'invoice_number': 'INV-2', 'supplier_tax_id': 'TAX1', 'invoice_date': '2024-01-01'},
    ]

    batch = validator.validate_batch(invoices)
    # both should be marked invalid because duplicate detection adds anomaly
    assert batch['summary']['duplicate_groups'] == 1
    assert batch['summary']['invalid_count'] == 2
