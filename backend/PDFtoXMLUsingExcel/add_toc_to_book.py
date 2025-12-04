#!/usr/bin/env python3
"""
Add Table of Contents to Book.XML in DTD-Compliant Way

This script adds a proper <toc> element to Book.XML that conforms to the
RittDoc DTD requirements.

DTD Structure for TOC:
  <!ELEMENT toc (beginpage?, title?, tocfront*, (tocpart|tocchap)*, tocback*)>
  <!ELEMENT tocchap (title?, tocentry*)>
  <!ELEMENT tocentry (#PCDATA|ulink|emphasis)*>

This is safer and more structured than using itemizedlist inside a chapter.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def extract_chapter_entities(book_xml_content: str) -> List[Tuple[str, str]]:
    """
    Extract chapter entity declarations from Book.XML.

    Returns:
        List of tuples: (entity_name, filename, chapter_title)
    """
    chapters = []

    # Find DOCTYPE declaration
    doctype_match = re.search(r'<!DOCTYPE[^>]+\[(.*?)\]>', book_xml_content, re.DOTALL)
    if not doctype_match:
        return chapters

    doctype_content = doctype_match.group(1)

    # Extract entity declarations: <!ENTITY ch0001 SYSTEM "ch0001.xml">
    entity_pattern = r'<!ENTITY\s+(ch\d+)\s+SYSTEM\s+"([^"]+)">'
    for match in re.finditer(entity_pattern, doctype_content):
        entity_name = match.group(1)
        filename = match.group(2)
        chapters.append((entity_name, filename))

    return chapters


def read_chapter_title(chapter_path: Path) -> str:
    """
    Extract title from a chapter XML file.

    Returns:
        Chapter title text, or empty string if not found
    """
    try:
        content = chapter_path.read_text(encoding='utf-8')

        # Find <title> element (first one after <chapter>)
        title_match = re.search(r'<chapter[^>]*>.*?<title[^>]*>(.*?)</title>', content, re.DOTALL)
        if title_match:
            title_text = title_match.group(1)

            # Clean up: remove any XML tags within title
            title_text = re.sub(r'<[^>]+>', '', title_text)
            title_text = title_text.strip()

            return title_text

    except Exception as e:
        print(f"Warning: Could not read title from {chapter_path}: {e}")

    return ""


def generate_toc_element(chapters: List[Tuple[str, str, str]]) -> str:
    """
    Generate a DTD-compliant <toc> element.

    Args:
        chapters: List of (entity_name, filename, title) tuples

    Returns:
        XML string for the <toc> element
    """
    toc_lines = [
        '  <toc>',
        '    <title>Table of Contents</title>',
    ]

    for entity_name, filename, title in chapters:
        if not title:
            title = filename  # Fallback to filename if no title found

        # Create tocchap element with tocentry
        toc_lines.append(f'    <tocchap>')
        toc_lines.append(f'      <tocentry>')
        toc_lines.append(f'        <ulink url="{filename}">{title}</ulink>')
        toc_lines.append(f'      </tocentry>')
        toc_lines.append(f'    </tocchap>')

    toc_lines.append('  </toc>')

    return '\n'.join(toc_lines)


def add_toc_to_book_xml(
    book_xml_path: Path,
    chapter_dir: Path,
    output_path: Path = None
) -> bool:
    """
    Add TOC element to Book.XML in a DTD-compliant way.

    Args:
        book_xml_path: Path to Book.XML file
        chapter_dir: Directory containing chapter XML files
        output_path: Optional output path (default: overwrite input)

    Returns:
        True if successful, False otherwise
    """
    if output_path is None:
        output_path = book_xml_path

    # Read Book.XML
    content = book_xml_path.read_text(encoding='utf-8')

    # Extract chapter entities
    chapter_entities = extract_chapter_entities(content)
    if not chapter_entities:
        print("Error: No chapter entities found in Book.XML")
        return False

    print(f"Found {len(chapter_entities)} chapter references")

    # Read chapter titles
    chapters_with_titles = []
    for entity_name, filename in chapter_entities:
        chapter_path = chapter_dir / filename
        title = read_chapter_title(chapter_path) if chapter_path.exists() else ""
        chapters_with_titles.append((entity_name, filename, title))
        if title:
            print(f"  {filename}: {title}")
        else:
            print(f"  {filename}: (no title found)")

    # Generate TOC element
    toc_xml = generate_toc_element(chapters_with_titles)

    # Find insertion point (after <bookinfo> and before first &ch reference)
    # Pattern: </bookinfo> ... &ch0001;
    insertion_pattern = r'(</bookinfo>.*?)(  &ch\d+;)'

    match = re.search(insertion_pattern, content, re.DOTALL)
    if not match:
        print("Error: Could not find insertion point for TOC")
        print("Looking for pattern: </bookinfo> ... &ch0001;")
        return False

    # Insert TOC
    new_content = content[:match.end(1)] + '\n' + toc_xml + '\n' + content[match.start(2):]

    # Write output
    output_path.write_text(new_content, encoding='utf-8')
    print(f"\n✓ TOC added successfully to {output_path}")
    print(f"  Added {len(chapters_with_titles)} chapter entries")

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Add DTD-compliant TOC to Book.XML"
    )
    parser.add_argument(
        "package_dir",
        help="Directory containing Book.XML and chapter files (e.g., extracted ZIP)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output Book.XML path (default: overwrite input)"
    )

    args = parser.parse_args()

    package_dir = Path(args.package_dir)
    if not package_dir.exists():
        print(f"Error: Directory not found: {package_dir}")
        sys.exit(1)

    book_xml_path = package_dir / "Book.XML"
    if not book_xml_path.exists():
        print(f"Error: Book.XML not found in {package_dir}")
        sys.exit(1)

    output_path = Path(args.output) if args.output else book_xml_path

    success = add_toc_to_book_xml(book_xml_path, package_dir, output_path)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
