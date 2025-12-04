#!/usr/bin/env python3
"""
Fix Chapter DTD Validation Violations (Simple Version - No lxml required)

This script fixes DTD validation errors in chapter XML files by wrapping
direct para/figure/table/list elements in sect1 sections.
"""

import re
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import List, Tuple

try:
    from validation_report import ValidationReportGenerator, VerificationItem
    VALIDATION_REPORT_AVAILABLE = True
except ImportError:
    VALIDATION_REPORT_AVAILABLE = False
    print("Note: validation_report module not found. Verification tracking disabled.")


def fix_chapter_content(xml_content: str, chapter_id: str) -> Tuple[str, int, List[int]]:
    """
    Fix chapter content by wrapping violating elements in sect1.

    Returns:
        Tuple of (fixed_content, num_fixes, wrapper_line_numbers)
    """
    lines = xml_content.split('\n')
    fixed_lines = []
    fixes = 0
    wrapper_line_numbers = []  # Track line numbers where wrappers were added

    # Elements that violate DTD when direct children of chapter
    VIOLATING_ELEMENTS = ['para', 'figure', 'table', 'orderedlist', 'itemizedlist']

    # Find chapter start
    in_chapter = False
    after_title = False
    wrapper_added = False
    wrapper_content = []
    wrapper_start_line = None
    indent = "    "

    for i, line in enumerate(lines):
        # Detect chapter start
        if '<chapter' in line and not in_chapter:
            in_chapter = True
            fixed_lines.append(line)
            continue

        # Detect title
        if in_chapter and '<title>' in line and not after_title:
            after_title = True
            fixed_lines.append(line)
            continue

        # Detect chapter end
        if '</chapter>' in line:
            # Close wrapper if open
            if wrapper_added:
                fixed_lines.append(f"{indent}</sect1>")
                fixes += len(wrapper_content)
                if wrapper_start_line:
                    wrapper_line_numbers.append(wrapper_start_line)
            fixed_lines.append(line)
            break

        # Check if this is a violating element (direct child of chapter)
        if in_chapter and after_title:
            stripped = line.strip()

            # Check if it's a violating element
            is_violating = False
            for elem in VIOLATING_ELEMENTS:
                if stripped.startswith(f'<{elem}') or stripped.startswith(f'<{elem}>'):
                    is_violating = True
                    break

            # Check if it's an allowed element (sect1, section, etc.)
            is_allowed = any(stripped.startswith(f'<{elem}') for elem in ['sect1', 'section', 'toc', 'lot', 'index', 'glossary', 'bibliography'])

            if is_violating and not wrapper_added:
                # Start wrapper
                wrapper_start_line = len(fixed_lines) + 1  # Track where wrapper starts
                fixed_lines.append(f'{indent}<sect1 id="{chapter_id}-intro">')
                fixed_lines.append(f'{indent}  <title>Introduction</title>')
                wrapper_added = True
                wrapper_content.append(line)
                fixed_lines.append(line)
            elif is_violating and wrapper_added:
                # Continue adding to wrapper
                wrapper_content.append(line)
                fixed_lines.append(line)
            elif is_allowed and wrapper_added:
                # Close wrapper before allowed element
                fixed_lines.append(f"{indent}</sect1>")
                fixes += len(wrapper_content)
                if wrapper_start_line:
                    wrapper_line_numbers.append(wrapper_start_line)
                wrapper_content = []
                wrapper_added = False
                wrapper_start_line = None
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines), fixes, wrapper_line_numbers


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
        print(f"Found {len(chapter_files)} chapter files to process")

        for chapter_file in sorted(chapter_files):
            stats['files_processed'] += 1

            # Read file
            content = chapter_file.read_text(encoding='utf-8')

            # Extract chapter ID from filename or content
            chapter_id = chapter_file.stem
            id_match = re.search(r'<chapter\s+id="([^"]+)"', content)
            if id_match:
                chapter_id = id_match.group(1)

            # Fix content
            fixed_content, num_fixes, wrapper_lines = fix_chapter_content(content, chapter_id)

            if num_fixes > 0:
                # Write back fixed content
                chapter_file.write_text(fixed_content, encoding='utf-8')
                stats['files_fixed'] += 1
                stats['total_fixes'] += num_fixes
                print(f"  ✓ Fixed {chapter_file.name}: {num_fixes} elements wrapped")

                # Add verification items for each wrapper
                if report and wrapper_lines:
                    for line_num in wrapper_lines:
                        report.add_verification_item(VerificationItem(
                            xml_file=chapter_file.name,
                            line_number=line_num,
                            fix_type="Content Model Fix - Wrapped Elements",
                            fix_description=f'Wrapped violating elements in <sect1 id="{chapter_id}-intro"> section',
                            verification_reason="Generic 'Introduction' title was auto-generated. The wrapped content may need a more descriptive section title.",
                            suggestion="Review the wrapped content and update the <title> element if a more specific title is appropriate."
                        ))

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
        report.generate_excel_report(report_path, "Chapter Content Model Fixes")
        print(f"✓ Verification report saved: {report_path}")
        print(f"  → {len(report.verification_items)} items require manual content verification")
        stats['verification_report'] = str(report_path)

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix DTD validation violations in RittDoc chapter XML files"
    )
    parser.add_argument("input", help="Input ZIP package")
    parser.add_argument("-o", "--output", help="Output ZIP path (default: add _fixed suffix)")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_fixed{input_path.suffix}"

    # Process ZIP
    stats = process_zip_package(input_path, output_path)

    # Print summary
    print("\n" + "=" * 70)
    print("FIX SUMMARY")
    print("=" * 70)
    print(f"Files processed:        {stats['files_processed']}")
    print(f"Files fixed:            {stats['files_fixed']}")
    print(f"Total elements wrapped: {stats['total_fixes']}")
    print(f"\nOutput: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
