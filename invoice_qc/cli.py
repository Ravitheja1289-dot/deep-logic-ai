"""
Command-line interface for invoice extraction and validation.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

import typer

from invoice_qc.extractor import extract_invoice
from invoice_qc.validator import validate_batch

app = typer.Typer()


def _find_pdf_files(pdf_dir: Path) -> List[Path]:
    """Find all PDF files in the given directory."""
    pdf_files = list(pdf_dir.glob("*.pdf"))
    pdf_files.extend(pdf_dir.glob("*.PDF"))
    return sorted(pdf_files)


def _print_summary(total: int, valid: int, invalid: int, error_counts: Dict[str, int]):
    """Print human-readable summary to stdout."""
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"Total invoices: {total}")
    print(f"Valid: {valid}")
    print(f"Invalid: {invalid}")
    
    if error_counts:
        print(f"\nTop 3 error types:")
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        for error_type, count in sorted_errors[:3]:
            print(f"  {error_type}: {count}")
    print(f"{'='*60}\n")


@app.command()
def extract(
    pdf_dir: str = typer.Option(..., "--pdf-dir", help="Directory containing PDF invoices"),
    output: str = typer.Option(..., "--output", help="Output JSON file path")
):
    """
    Extract invoice data from PDF files in a directory.
    """
    pdf_dir_path = Path(pdf_dir)
    output_path = Path(output)
    
    if not pdf_dir_path.exists():
        typer.echo(f"Error: Directory '{pdf_dir}' does not exist", err=True)
        raise typer.Exit(code=1)
    
    if not pdf_dir_path.is_dir():
        typer.echo(f"Error: '{pdf_dir}' is not a directory", err=True)
        raise typer.Exit(code=1)
    
    pdf_files = _find_pdf_files(pdf_dir_path)
    
    if not pdf_files:
        typer.echo(f"Warning: No PDF files found in '{pdf_dir}'", err=True)
        invoices = []
    else:
        typer.echo(f"Found {len(pdf_files)} PDF file(s). Extracting...")
        invoices = []
        
        for pdf_file in pdf_files:
            try:
                typer.echo(f"Processing: {pdf_file.name}")
                invoice_data = extract_invoice(str(pdf_file))
                invoices.append(invoice_data)
            except Exception as e:
                typer.echo(f"Error extracting {pdf_file.name}: {e}", err=True)
                continue
    
    # Write output JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(invoices, f, indent=2, ensure_ascii=False)
    
    typer.echo(f"\nExtracted {len(invoices)} invoice(s). Output written to: {output_path}")
    
    # Print summary
    _print_summary(
        total=len(invoices),
        valid=len(invoices),  # All extracted invoices are considered "processed"
        invalid=0,
        error_counts={}
    )


@app.command()
def validate(
    input: str = typer.Option(..., "--input", help="Input JSON file with invoices"),
    report: str = typer.Option(..., "--report", help="Output validation report JSON file path")
):
    """
    Validate invoices from a JSON file.
    """
    input_path = Path(input)
    report_path = Path(report)
    
    if not input_path.exists():
        typer.echo(f"Error: Input file '{input}' does not exist", err=True)
        raise typer.Exit(code=1)
    
    # Read invoices
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            invoices = json.load(f)
    except json.JSONDecodeError as e:
        typer.echo(f"Error: Invalid JSON in '{input}': {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error reading '{input}': {e}", err=True)
        raise typer.Exit(code=1)
    
    if not isinstance(invoices, list):
        typer.echo(f"Error: Input JSON must be a list of invoices", err=True)
        raise typer.Exit(code=1)
    
    typer.echo(f"Validating {len(invoices)} invoice(s)...")
    
    # Validate batch
    validation_result = validate_batch(invoices)
    
    # Write report JSON
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(validation_result, f, indent=2, ensure_ascii=False)
    
    summary = validation_result['summary']
    
    # Print summary
    _print_summary(
        total=summary['total_invoices'],
        valid=summary['valid_count'],
        invalid=summary['invalid_count'],
        error_counts=summary['error_counts']
    )
    
    typer.echo(f"Validation report written to: {report_path}")
    
    # Exit with non-zero if invalid invoices exist
    if summary['invalid_count'] > 0:
        typer.echo(f"Validation failed: {summary['invalid_count']} invalid invoice(s) found", err=True)
        raise typer.Exit(code=1)


@app.command()
def full_run(
    pdf_dir: str = typer.Option(..., "--pdf-dir", help="Directory containing PDF invoices"),
    report: str = typer.Option(..., "--report", help="Output validation report JSON file path")
):
    """
    Extract invoices from PDFs and validate them in one operation.
    """
    pdf_dir_path = Path(pdf_dir)
    report_path = Path(report)
    
    if not pdf_dir_path.exists():
        typer.echo(f"Error: Directory '{pdf_dir}' does not exist", err=True)
        raise typer.Exit(code=1)
    
    if not pdf_dir_path.is_dir():
        typer.echo(f"Error: '{pdf_dir}' is not a directory", err=True)
        raise typer.Exit(code=1)
    
    pdf_files = _find_pdf_files(pdf_dir_path)
    
    if not pdf_files:
        typer.echo(f"Warning: No PDF files found in '{pdf_dir}'", err=True)
        invoices = []
    else:
        typer.echo(f"Found {len(pdf_files)} PDF file(s). Extracting...")
        invoices = []
        
        for pdf_file in pdf_files:
            try:
                typer.echo(f"Processing: {pdf_file.name}")
                invoice_data = extract_invoice(str(pdf_file))
                invoices.append(invoice_data)
            except Exception as e:
                typer.echo(f"Error extracting {pdf_file.name}: {e}", err=True)
                continue
    
    if not invoices:
        typer.echo("No invoices extracted. Exiting.", err=True)
        raise typer.Exit(code=1)
    
    typer.echo(f"\nValidating {len(invoices)} invoice(s)...")
    
    # Validate batch
    validation_result = validate_batch(invoices)
    
    # Write report JSON
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(validation_result, f, indent=2, ensure_ascii=False)
    
    summary = validation_result['summary']
    
    # Print summary
    _print_summary(
        total=summary['total_invoices'],
        valid=summary['valid_count'],
        invalid=summary['invalid_count'],
        error_counts=summary['error_counts']
    )
    
    typer.echo(f"Validation report written to: {report_path}")
    
    # Exit with non-zero if invalid invoices exist
    if summary['invalid_count'] > 0:
        typer.echo(f"Validation failed: {summary['invalid_count']} invalid invoice(s) found", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()


