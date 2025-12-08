
import pytest
from invoice_qc import regex_patterns

def test_extract_tax_id_vat():
    text = "Supplier Name\nVAT: DE123456789\nAddress"
    assert regex_patterns.extract_tax_id(text) == "DE123456789"

def test_extract_tax_id_gst():
    text = "GSTIN: 29ABCDE1234F1Z5"
    assert regex_patterns.extract_tax_id(text) == "29ABCDE1234F1Z5"

def test_extract_tax_id_label_variations():
    assert regex_patterns.extract_tax_id("Tax ID: 12-3456789") == "12-3456789"
    assert regex_patterns.extract_tax_id("UST-IDNr: DE999999999") == "DE999999999"
    assert regex_patterns.extract_tax_id("UID: CHE-123.456.789") == "CHE-123.456.789"

def test_extract_tax_id_none():
    assert regex_patterns.extract_tax_id("No tax id here") is None
