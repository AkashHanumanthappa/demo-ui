#!/usr/bin/env python3
"""
Fix Misclassified Figures that Should Be Tables

This script detects and fixes cases where:
1. A <figure> element has "Table" in its title
2. The figure only contains an empty <mediaobject> (placeholder)
3. The next sibling element is a <table> with the actual table data

The fix:
- Removes the empty figure element
- Updates the table to use the descriptive title from the figure
- Preserves all table data (tgroup, rows, entries)

Common pattern from EPUB conversion:
  <figure><title>Table 10.9–3 Examples of tests</title>
    <mediaobject><textobject><phrase>Image not available</phrase></textobject></mediaobject>
  </figure>
  <table><title>Table 1</title>
    <tgroup cols="2">...</tgroup>
  </table>

Should become:
  <table><title>Table 10.9–3 Examples of tests</title>
    <tgroup cols="2">...</tgroup>
  </table>
"""

import re
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Tuple, List, Optional

try:
    from validation_report import ValidationReportGenerator, VerificationItem
    VALIDATION_REPORT_AVAILABLE = True
except ImportError:
    VALIDATION_REPORT_AVAILABLE = False
    print("Note: validation_report module not found. Verification tracking disabled.")


def fix_misclassified_figures(xml_content: str) -> Tuple[str, int, List[Tuple[int, str]]]:
    """
    Fix figures that should be tables.

    Args:
        xml_content: XML content as string

    Returns:
        Tuple of (fixed_content, num_fixes, fix_details)
        where fix_details is a list of (line_number, table_title) tuples
    """
    fixes = 0
    fix_details = []  # Track (line_number, title) for verification

    # Pattern to find figure with "Table" in title followed by table element
    # This regex finds:
    # 1. <figure> ... <title>...Table...</title> ... </figure>
    # 2. Optionally some whitespace
    # 3. <table> ... </table>

    pattern = r'''
        (<figure[^>]*>)           # Group 1: opening figure tag
        (.*?)                      # Group 2: figure content
        (<title[^>]*>)            # Group 3: opening title tag
        (.*?\bTable\b.*?)         # Group 4: title text containing "Table"
        (</title>)                 # Group 5: closing title tag
        (.*?)                      # Group 6: rest of figure content
        (</figure>)                # Group 7: closing figure tag
        \s*                        # Optional whitespace
        (<table[^>]*>)            # Group 8: opening table tag (NEXT SIBLING)
        (.*?)                      # Group 9: table content
        (</table>)                 # Group 10: closing table tag
    '''

    def replace_func(match):
        nonlocal fixes

        figure_start = match.group(1)
        figure_content = match.group(2)
        title_start = match.group(3)
        title_text = match.group(4)
        title_end = match.group(5)
        figure_rest = match.group(6)
        figure_end = match.group(7)
        table_start = match.group(8)
        table_content = match.group(9)
        table_end = match.group(10)

        # Check if the figure has only empty mediaobject (placeholder)
        # Look for "Image not available" or empty mediaobject
        has_real_image = bool(re.search(r'<imagedata\s+fileref="[^"]+"', figure_rest))
        is_placeholder = bool(re.search(r'Image not available|No image available', figure_rest, re.IGNORECASE))

        # Check if table has actual content (tgroup, rows, etc.)
        has_table_data = bool(re.search(r'<(tgroup|tbody|row|entry)', table_content))

        if (is_placeholder or not has_real_image) and has_table_data:
            # This is a misclassified figure - convert to table

            # Extract the real table title (from figure) or use existing
            real_title = f"{title_start}{title_text}{title_end}"

            # Replace generic table title with the descriptive one from figure
            # Pattern: <title>Table \d+</title> or similar generic titles
            table_with_new_title = re.sub(
                r'<title[^>]*>.*?</title>',
                real_title,
                table_content,
                count=1,
                flags=re.DOTALL
            )

            # Track this fix for verification
            # Calculate approximate line number (count newlines before match)
            match_start = match.start()
            line_num = xml_content[:match_start].count('\n') + 1
            fix_details.append((line_num, title_text.strip()))

            # Return just the table (no figure)
            fixes += 1
            return f"{table_start}{table_with_new_title}{table_end}"

        # Not a misclassification, return original
        return match.group(0)

    # Apply the fix
    fixed_content = re.sub(
        pattern,
        replace_func,
        xml_content,
        flags=re.VERBOSE | re.DOTALL | re.IGNORECASE
    )

    return fixed_content, fixes, fix_details


def process_chapter_file(chapter_path: Path) -> Tuple[int, str, List[Tuple[int, str]]]:
    """
    Process a single chapter XML file.

    Returns:
        Tuple of (num_fixes, status_message, fix_details)
    """
    try:
        content = chapter_path.read_text(encoding='utf-8')
        fixed_content, fixes, fix_details = fix_misclassified_figures(content)

        if fixes > 0:
            chapter_path.write_text(fixed_content, encoding='utf-8')
            return fixes, "fixed", fix_details

        return 0, "ok", []

    except Exception as e:
        return 0, f"error: {e}", []


def process_zip_package(zip_path: Path, output_path: Path, generate_verification_report: bool = True) -> dict:
    """
    Process all chapter files in a ZIP package.

    Args:
        zip_path: Path to input ZIP
        output_path: Path to output ZIP
        generate_verification_report: If True, generate Excel report with verification items

    Returns:
        Dictionary with statistics
    """
    stats = {
        'files_processed': 0,
        'files_fixed': 0,
        'total_fixes': 0
    }

    # Create validation report generator if available
    report = None
    if VALIDATION_REPORT_AVAILABLE and generate_verification_report:
        report = ValidationReportGenerator()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Extract ZIP
        print(f"Extracting {zip_path.name}...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        # Find all chapter XML files
        chapter_files = list(extract_dir.rglob("ch*.xml"))
        print(f"Found {len(chapter_files)} chapter files to process\n")

        for chapter_file in sorted(chapter_files):
            stats['files_processed'] += 1

            fixes, status, fix_details = process_chapter_file(chapter_file)

            if fixes > 0:
                stats['files_fixed'] += 1
                stats['total_fixes'] += fixes
                print(f"  ✓ {chapter_file.name}: Fixed {fixes} misclassified figure(s)")

                # Add verification items for each fix
                if report and fix_details:
                    for line_num, table_title in fix_details:
                        report.add_verification_item(VerificationItem(
                            xml_file=chapter_file.name,
                            line_number=line_num,
                            fix_type="Misclassified Figure Conversion",
                            fix_description=f'Converted empty <figure> to <table> with title: "{table_title}"',
                            verification_reason="Automated conversion merged figure title with table data. Verify table structure and title are correct.",
                            suggestion="Review the table structure (tgroup, rows, entries) and ensure the title accurately describes the table content."
                        ))

            elif status.startswith("error"):
                print(f"  ✗ {chapter_file.name}: {status}")

        # Recreate ZIP
        print(f"\nCreating fixed ZIP: {output_path.name}...")
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in extract_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(extract_dir)
                    zf.write(file_path, arcname)

    # Return verification items for external use
    stats['verification_items'] = report.verification_items if report else []

    # Generate verification report if we have items
    if report and report.verification_items and generate_verification_report:
        report_path = output_path.parent / f"{output_path.stem}_verification_report.xlsx"
        print(f"\nGenerating verification report: {report_path.name}...")
        report.generate_excel_report(report_path, "Misclassified Figure Fixes")
        print(f"✓ Verification report saved: {report_path}")
        print(f"  → {len(report.verification_items)} items require manual content verification")
        stats['verification_report'] = str(report_path)

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix misclassified figures that should be tables"
    )
    parser.add_argument("input", help="Input ZIP package")
    parser.add_argument(
        "-o", "--output",
        help="Output ZIP path (default: add _tables_fixed suffix)"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_tables_fixed{input_path.suffix}"

    # Process ZIP
    print("=" * 70)
    print("FIX MISCLASSIFIED FIGURES (SHOULD BE TABLES)")
    print("=" * 70)

    stats = process_zip_package(input_path, output_path)

    # Print summary
    print("\n" + "=" * 70)
    print("FIX SUMMARY")
    print("=" * 70)
    print(f"Files processed:           {stats['files_processed']}")
    print(f"Files with fixes:          {stats['files_fixed']}")
    print(f"Total figures converted:   {stats['total_fixes']}")
    print(f"\nOutput: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
