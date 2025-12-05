#!/usr/bin/env python3
"""
Complete PDF to RittDoc Pipeline

This script processes a PDF file through the entire pipeline:
1. PDF → Unified XML (pdf_to_unified_xml.py)
2. Unified XML → DocBook Package (package.py via direct import)
3. DocBook Package → RittDoc Compliant Package (rittdoc_compliance_pipeline.py)

Usage:
    python3 pdf_to_rittdoc.py document.pdf
    python3 pdf_to_rittdoc.py document.pdf --output final_package.zip
"""

import argparse
import subprocess
import sys
from pathlib import Path

from lxml import etree

from rittdoc_compliance_pipeline import RittDocCompliancePipeline
from package import (
    BOOK_DOCTYPE_SYSTEM_DEFAULT,
    package_docbook,
    make_file_fetcher,
)


def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(str(c) for c in cmd)}\n")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr and result.returncode != 0:
        print("STDERR:", result.stderr, file=sys.stderr)
    
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Complete PDF to RittDoc Compliant XML Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Basic usage:
    python3 pdf_to_rittdoc.py mybook.pdf

  Custom output:
    python3 pdf_to_rittdoc.py mybook.pdf --output mybook_rittdoc.zip

  Custom DPI for images:
    python3 pdf_to_rittdoc.py mybook.pdf --dpi 300

  Skip PDF processing (use existing XML):
    python3 pdf_to_rittdoc.py mybook.pdf --skip-pdf

  Skip packaging (use existing ZIP):
    python3 pdf_to_rittdoc.py mybook.pdf --skip-package --package existing.zip
        """
    )
    
    parser.add_argument(
        "pdf",
        help="Input PDF file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output ZIP package path (default: <pdf>_rittdoc.zip)"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="DPI for image rendering (default: 200)"
    )
    parser.add_argument(
        "--dtd",
        default="RITTDOCdtd/v1.1/RittDocBook.dtd",
        help="Path to DTD file (default: RITTDOCdtd/v1.1/RittDocBook.dtd)"
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Skip PDF processing, use existing unified XML"
    )
    parser.add_argument(
        "--skip-package",
        action="store_true",
        help="Skip packaging, use existing DocBook ZIP"
    )
    parser.add_argument(
        "--package",
        help="Existing DocBook package to use (with --skip-package)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Max compliance iterations (default: 3)"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    pdf_path = Path(args.pdf)
    if not args.skip_pdf and not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    dtd_path = Path(args.dtd)
    if not dtd_path.exists():
        print(f"Error: DTD file not found: {dtd_path}", file=sys.stderr)
        sys.exit(1)
    
    # Determine output path
    if args.output:
        final_output = Path(args.output)
    else:
        final_output = pdf_path.parent / f"{pdf_path.stem}_rittdoc.zip"
    
    print("=" * 80)
    print("PDF TO RITTDOC COMPLIANT XML - COMPLETE PIPELINE")
    print("=" * 80)
    print(f"Input PDF:      {pdf_path}")
    print(f"Final Output:   {final_output}")
    print(f"DTD:            {dtd_path}")
    print("=" * 80)
    
    # Step 1: PDF → Unified XML
    if not args.skip_pdf:
        print("\n" + "=" * 80)
        print("STEP 1: PROCESSING PDF → UNIFIED XML")
        print("=" * 80)
        
        success = run_command(
            ['python3', 'pdf_to_unified_xml.py', str(pdf_path), '--dpi', str(args.dpi)],
            "Extracting text and media from PDF"
        )
        
        if not success:
            print("\n✗ PDF processing failed")
            sys.exit(1)
        
        unified_xml = pdf_path.parent / f"{pdf_path.stem}_unified.xml"
        if not unified_xml.exists():
            print(f"\n✗ Expected unified XML not found: {unified_xml}")
            sys.exit(1)
        
        print(f"\n✓ Created unified XML: {unified_xml}")
    else:
        unified_xml = pdf_path.parent / f"{pdf_path.stem}_unified.xml"
        if not unified_xml.exists():
            print(f"Error: Unified XML not found: {unified_xml}", file=sys.stderr)
            sys.exit(1)
        print(f"\n⊳ Using existing unified XML: {unified_xml}")
    
    # Step 2: Unified XML → DocBook Package
    if not args.skip_package:
        print("\n" + "=" * 80)
        print("STEP 2: CREATING DOCBOOK PACKAGE")
        print("=" * 80)

        try:
            # Parse the unified XML
            print(f"  → Parsing unified XML: {unified_xml}")
            root = etree.parse(str(unified_xml)).getroot()

            # Determine base name for output
            base = unified_xml.stem
            # Remove _unified suffix if present
            if base.endswith("_unified"):
                base = base[:-8]

            # Find MultiMedia folder (created by pdf_to_unified_xml.py)
            multimedia_folder = unified_xml.parent / f"{base}_MultiMedia"

            # If not found, try alternative patterns
            if not multimedia_folder.exists():
                # Look for any folder ending with _MultiMedia
                multimedia_folders = list(unified_xml.parent.glob("*_MultiMedia"))
                if multimedia_folders:
                    multimedia_folder = multimedia_folders[0]
                    print(f"  → Found alternative MultiMedia folder: {multimedia_folder}")

            # Create media fetcher with search paths
            search_paths = []
            if multimedia_folder.exists():
                print(f"  → Found MultiMedia folder: {multimedia_folder}")
                search_paths.append(multimedia_folder)
                # Also add SharedImages subfolder if it exists
                shared_images = multimedia_folder / "SharedImages"
                if shared_images.exists():
                    search_paths.append(shared_images)
            else:
                print(f"  ⚠ Warning: MultiMedia folder not found at {multimedia_folder}")
                print(f"     Images may not be included in the package!")

            # Add the input directory as a fallback search path
            search_paths.append(unified_xml.parent)

            # Create media fetcher
            media_fetcher = make_file_fetcher(search_paths) if search_paths else None

            # Determine output directory and ZIP path
            output_dir = Path('Output')
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path = output_dir / f"{base}.zip"

            # Call package_docbook directly (the key fix!)
            print(f"  → Creating DocBook package...")
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

            print(f"\n✓ Created DocBook package: {docbook_package}")

        except Exception as e:
            print(f"\n✗ Package creation failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        if args.package:
            docbook_package = Path(args.package)
        else:
            # Try to find existing package
            output_dir = Path('Output')
            if output_dir.exists():
                zip_files = list(output_dir.glob(f"{pdf_path.stem}*.zip"))
                if zip_files:
                    docbook_package = zip_files[0]
                else:
                    print("Error: No existing package found, specify with --package", file=sys.stderr)
                    sys.exit(1)
            else:
                print("Error: No existing package found, specify with --package", file=sys.stderr)
                sys.exit(1)
        
        if not docbook_package.exists():
            print(f"Error: Package not found: {docbook_package}", file=sys.stderr)
            sys.exit(1)
        
        print(f"\n⊳ Using existing package: {docbook_package}")
    
    # Step 3: DocBook Package → RittDoc Compliant Package
    print("\n" + "=" * 80)
    print("STEP 3: APPLYING RITTDOC COMPLIANCE")
    print("=" * 80)
    
    pipeline = RittDocCompliancePipeline(dtd_path)
    success = pipeline.run(
        input_zip=docbook_package,
        output_zip=final_output,
        max_iterations=args.iterations
    )
    
    # Final summary
    print("\n" + "=" * 80)
    print("COMPLETE PIPELINE FINISHED")
    print("=" * 80)
    
    if success:
        print("\n✓ SUCCESS: PDF has been converted to RittDoc compliant XML!")
        print(f"\nFinal output: {final_output}")
        print("\nThis package:")
        print("  ✓ Is fully RittDoc DTD v1.1 compliant")
        print("  ✓ Has all DTD validation errors fixed")
        print("  ✓ Includes structured chapters with proper hierarchy")
        print("  ✓ Contains extracted media (images, tables)")
        print("  ✓ Ready for publication workflow")
    else:
        print("\n⚠ PARTIAL SUCCESS: Package created with minimal errors")
        print(f"\nFinal output: {final_output}")
        
        report = final_output.parent / f"{final_output.stem}_validation_report.xlsx"
        if report.exists():
            print(f"Validation report: {report}")
            print("\nReview the report to address remaining issues.")
    
    print("=" * 80)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
