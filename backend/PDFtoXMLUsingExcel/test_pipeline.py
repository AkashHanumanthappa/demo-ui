#!/usr/bin/env python3
"""
Test script to demonstrate the complete RittDoc compliance pipeline

This script:
1. Processes a PDF to generate XML DocBook package (if needed)
2. Runs the complete compliance pipeline
3. Validates the final output
"""

import sys
import subprocess
from pathlib import Path

from lxml import etree

from package import (
    BOOK_DOCTYPE_SYSTEM_DEFAULT,
    package_docbook,
    make_file_fetcher,
)


def run_command(cmd, description):
    """Run a command and print output"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)
    
    return result.returncode == 0


def main():
    """Run end-to-end test"""
    
    # Check for test data
    pdf_files = list(Path('.').glob('*.pdf'))
    
    if not pdf_files:
        print("No PDF files found in current directory.")
        print("Please provide a PDF file to test the pipeline.")
        sys.exit(1)
    
    # Use first PDF file
    pdf_file = pdf_files[0]
    print(f"Using test PDF: {pdf_file}")
    
    # Step 1: Generate XML package from PDF (if package.py exists)
    package_script = Path('package.py')
    if package_script.exists():
        print("\n" + "="*80)
        print("STEP 1: GENERATING XML DOCBOOK PACKAGE FROM PDF")
        print("="*80)

        # First run pdf_to_unified_xml.py to generate the XML
        success = run_command(
            ['python3', 'pdf_to_unified_xml.py', str(pdf_file)],
            "Generating unified XML from PDF"
        )

        if not success:
            print("Warning: PDF to XML conversion had issues, continuing anyway...")

        # Create DocBook package using direct function call (fixed!)
        unified_xml = pdf_file.with_suffix('_unified.xml')
        if unified_xml.exists():
            try:
                print("\n" + "="*80)
                print("Creating DocBook package")
                print("="*80)

                # Parse the unified XML
                root = etree.parse(str(unified_xml)).getroot()

                # Determine base name
                base = unified_xml.stem
                if base.endswith("_unified"):
                    base = base[:-8]

                # Find MultiMedia folder
                multimedia_folder = unified_xml.parent / f"{base}_MultiMedia"
                search_paths = []
                if multimedia_folder.exists():
                    search_paths.append(multimedia_folder)
                search_paths.append(unified_xml.parent)

                # Create media fetcher
                media_fetcher = make_file_fetcher(search_paths) if search_paths else None

                # Output directory and ZIP path
                output_dir = Path('Output')
                output_dir.mkdir(parents=True, exist_ok=True)
                zip_path = output_dir / f"{base}.zip"

                # Call package_docbook directly
                docbook_package = package_docbook(
                    root=root,
                    root_name=(root.tag.split('}', 1)[-1] if root.tag.startswith('{') else root.tag),
                    dtd_system=BOOK_DOCTYPE_SYSTEM_DEFAULT,
                    zip_path=str(zip_path),
                    processing_instructions=[],
                    assets=[],
                    media_fetcher=media_fetcher,
                    book_doctype_system=BOOK_DOCTYPE_SYSTEM_DEFAULT,
                    metadata_dir=unified_xml.parent,
                )
                print(f"✓ Created DocBook package: {docbook_package}")

            except Exception as e:
                print(f"Error: Failed to create DocBook package: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
        else:
            print(f"Error: Unified XML not found: {unified_xml}")
            sys.exit(1)
    
    # Find generated ZIP package
    zip_files = list(Path('.').glob('*.zip'))
    output_dir = Path('Output')
    if output_dir.exists():
        zip_files.extend(list(output_dir.glob('*.zip')))
    
    if not zip_files:
        print("No ZIP packages found. Skipping to validation test with demo files.")
        # Use demo XML for testing
        demo_zip = create_demo_package()
        if not demo_zip:
            print("Error: Could not create demo package")
            sys.exit(1)
        test_zip = demo_zip
    else:
        test_zip = zip_files[0]
        print(f"\nUsing test package: {test_zip}")
    
    # Step 2: Run compliance pipeline
    print("\n" + "="*80)
    print("STEP 2: RUNNING RITTDOC COMPLIANCE PIPELINE")
    print("="*80)
    
    success = run_command(
        ['python3', 'rittdoc_compliance_pipeline.py', str(test_zip)],
        "Running complete compliance pipeline"
    )
    
    if not success:
        print("\n⚠ Pipeline completed with warnings or errors")
        print("Check the output above for details")
    
    # Find output package
    output_zip = test_zip.parent / f"{test_zip.stem}_rittdoc_compliant.zip"
    
    if output_zip.exists():
        print(f"\n✓ Output package created: {output_zip}")
        
        # Check for validation report
        report_file = output_zip.parent / f"{output_zip.stem}_validation_report.xlsx"
        if report_file.exists():
            print(f"✓ Validation report created: {report_file}")
    else:
        print(f"\n✗ Expected output not found: {output_zip}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    
    return success


def create_demo_package():
    """Create a simple demo package for testing"""
    import tempfile
    import zipfile
    from lxml import etree
    
    print("\nCreating demo package for testing...")
    
    # Create a simple DocBook XML structure
    book = etree.Element("book")
    book.set("id", "demo-book")
    
    bookinfo = etree.SubElement(book, "bookinfo")
    title = etree.SubElement(bookinfo, "title")
    title.text = "Demo Book for Testing"
    
    chapter = etree.SubElement(book, "chapter")
    chapter.set("id", "ch01")
    ch_title = etree.SubElement(chapter, "title")
    ch_title.text = "Chapter 1"
    
    para = etree.SubElement(chapter, "para")
    para.text = "This is a test paragraph."
    
    # Create Book.XML
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Write Book.XML
        book_xml = tmp_path / "Book.XML"
        tree = etree.ElementTree(book)
        tree.write(str(book_xml), encoding='utf-8', xml_declaration=True, pretty_print=True)
        
        # Create ZIP
        demo_zip = Path("demo_package.zip")
        with zipfile.ZipFile(demo_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(book_xml, "Book.XML")
        
        print(f"✓ Created demo package: {demo_zip}")
        return demo_zip


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
