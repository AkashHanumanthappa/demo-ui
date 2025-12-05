#!/usr/bin/env python3
"""
Fix Chapter DTD Validation Violations

This script fixes three types of DTD validation errors in chapter XML files:
1. Invalid chapter content model - wraps direct para/figure/table/list elements in sect1
2. Nested para elements - flattens nested para elements
3. Empty table rows - removes empty row elements

According to the RittDoc DTD (ritthier2.mod), chapters can only contain:
- beginpage? chapterinfo? title tocchap? (toc|lot|index|glossary|bibliography|sect1)*

They CANNOT have direct para, figure, table, orderedlist, itemizedlist children.
"""

import logging
import sys
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import List, Set

from lxml import etree

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def _local_name(element: etree._Element) -> str:
    """Extract local name from element tag."""
    tag = element.tag
    if not isinstance(tag, str):
        return ""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _is_inline_only(element: etree._Element) -> bool:
    """
    Check if an element contains only inline content (no block elements).

    Block elements include: itemizedlist, orderedlist, figure, table, sect*, etc.
    Inline elements include: emphasis, ulink, subscript, superscript, anchor, etc.
    """
    BLOCK_ELEMENTS = {
        'itemizedlist', 'orderedlist', 'variablelist', 'simplelist',
        'figure', 'informalfigure', 'table', 'informaltable',
        'example', 'informalexample',
        'programlisting', 'screen', 'literallayout',
        'blockquote', 'note', 'warning', 'caution', 'important', 'tip',
        'sect1', 'sect2', 'sect3', 'sect4', 'sect5', 'section',
        'para'  # Nested para is also a block element
    }

    # Check all child elements
    for child in element:
        if isinstance(child.tag, str):
            local = _local_name(child)
            if local in BLOCK_ELEMENTS:
                return False
            # Recursively check children
            if not _is_inline_only(child):
                return False

    return True


def fix_nested_para_elements(root: etree._Element) -> int:
    """
    Fix nested para elements by intelligently unwrapping or flattening them.

    Strategy:
    1. If nested para contains ONLY inline elements (links, emphasis, etc.):
       -> Unwrap it: merge its content into the parent para
    2. If nested para contains block elements (lists, tables, etc.):
       -> Flatten it: create sibling para elements

    This preserves links and formatting while fixing DTD violations.

    Returns:
        Number of fixes made
    """
    fixes = 0
    # Find all para elements that contain other para elements
    for para in root.findall(".//para"):
        nested_paras = [child for child in para if isinstance(child.tag, str) and _local_name(child) == "para"]

        if not nested_paras:
            continue

        parent = para.getparent()
        if parent is None:
            continue

        # Check if we can unwrap (inline-only) or need to flatten (has block content)
        for nested_para in nested_paras:
            if _is_inline_only(nested_para):
                # UNWRAP: Nested para has only inline content (links, emphasis, etc.)
                # Move its content directly into parent para, preserving all inline elements

                # Get position of nested para within parent para
                nested_index = list(para).index(nested_para)

                # Insert nested para's children before it
                for i, child in enumerate(list(nested_para)):
                    para.insert(nested_index + i, child)

                # Handle text content
                if nested_para.text:
                    if nested_index > 0:
                        # Add to previous sibling's tail
                        prev = para[nested_index - 1]
                        prev.tail = (prev.tail or '') + nested_para.text
                    else:
                        # Add to parent para's text
                        para.text = (para.text or '') + nested_para.text

                # Handle tail text (text after nested para)
                if nested_para.tail:
                    # Find last inserted child and append to its tail
                    if len(nested_para) > 0:
                        last_child = para[nested_index + len(nested_para) - 1]
                        last_child.tail = (last_child.tail or '') + nested_para.tail
                    elif nested_index > 0:
                        prev = para[nested_index - 1]
                        prev.tail = (prev.tail or '') + nested_para.tail
                    else:
                        para.text = (para.text or '') + nested_para.tail

                # Remove the nested para element itself
                para.remove(nested_para)
                fixes += 1
                logger.debug(f"Unwrapped inline-only nested para with id={nested_para.get('id')}")

            else:
                # FLATTEN: Nested para has block content - create sibling paras
                para_index = list(parent).index(para)

                # Create new para element at parent level
                new_para = etree.Element("para")
                if nested_para.get("id"):
                    new_para.set("id", nested_para.get("id"))

                # Copy text and children
                new_para.text = nested_para.text
                for child in nested_para:
                    new_para.append(deepcopy(child))

                # Insert after current para
                para_index += 1
                parent.insert(para_index, new_para)

                # Handle tail text: if there's text after the nested para,
                # wrap it in a new para element
                if nested_para.tail and nested_para.tail.strip():
                    tail_para = etree.Element("para")
                    tail_para.text = nested_para.tail
                    para_index += 1
                    parent.insert(para_index, tail_para)
                    logger.debug(f"Created additional para for tail text: '{nested_para.tail.strip()[:50]}'")

                # Remove from original para
                para.remove(nested_para)
                fixes += 1
                logger.debug(f"Flattened block-content nested para with id={nested_para.get('id')}")

    return fixes


def fix_empty_table_rows(root: etree._Element) -> int:
    """
    Remove empty table row elements.

    Returns:
        Number of fixes made
    """
    fixes = 0
    for row in root.findall(".//row"):
        # Check if row has no entry children
        entries = [child for child in row if isinstance(child.tag, str) and _local_name(child) == "entry"]

        if not entries and not (row.text or "").strip():
            # Empty row - remove it
            parent = row.getparent()
            if parent is not None:
                parent.remove(row)
                fixes += 1
                logger.debug(f"Removed empty table row")

    return fixes


def wrap_chapter_content_in_sect1(chapter: etree._Element) -> int:
    """
    Wrap non-compliant chapter content in sect1 elements.

    According to DTD, chapters can only contain:
    - beginpage?, chapterinfo?, title, tocchap?, (toc|lot|index|glossary|bibliography|sect1)*

    This function wraps all para, figure, table, orderedlist, itemizedlist, etc. elements
    that appear as direct children of chapter into sect1 sections.

    Returns:
        Number of fixes made (0 or 1, since we create at most one wrapper sect1)
    """
    # Elements allowed as direct chapter children (per DTD)
    ALLOWED_BEFORE_BODY = {"beginpage", "chapterinfo", "title", "tocchap"}
    ALLOWED_BODY = {"toc", "lot", "index", "glossary", "bibliography", "sect1", "section"}

    # Find first non-allowed element
    needs_wrapping = []
    first_allowed_body_index = None

    for idx, child in enumerate(chapter):
        if not isinstance(child.tag, str):
            continue

        local = _local_name(child)

        # Skip allowed header elements
        if local in ALLOWED_BEFORE_BODY:
            continue

        # If we encounter an allowed body element, note its position
        if local in ALLOWED_BODY:
            if first_allowed_body_index is None:
                first_allowed_body_index = idx
            continue

        # This element needs to be wrapped
        needs_wrapping.append((idx, child))

    if not needs_wrapping:
        return 0

    # Group consecutive elements that need wrapping
    # We'll wrap all elements that appear BEFORE the first sect1/section
    pre_section_elements = []
    for idx, child in needs_wrapping:
        if first_allowed_body_index is None or idx < first_allowed_body_index:
            pre_section_elements.append(child)

    if not pre_section_elements:
        return 0

    # Create a sect1 wrapper
    sect1 = etree.Element("sect1")

    # Generate ID for the sect1
    chapter_id = chapter.get("id", "")
    if chapter_id:
        sect1.set("id", f"{chapter_id}-intro")

    # Add a title (required by DTD for sect1)
    sect1_title = etree.SubElement(sect1, "title")

    # Try to derive a meaningful title from chapter title
    chapter_title_elem = chapter.find("title")
    if chapter_title_elem is not None:
        chapter_title_text = "".join(chapter_title_elem.itertext()).strip()
        sect1_title.text = "Introduction"  # Generic title
    else:
        sect1_title.text = "Content"

    # Move elements into sect1
    for elem in pre_section_elements:
        chapter.remove(elem)
        sect1.append(elem)

    # Insert sect1 after title/header elements
    insert_position = 0
    for idx, child in enumerate(chapter):
        if not isinstance(child.tag, str):
            continue
        local = _local_name(child)
        if local in ALLOWED_BEFORE_BODY:
            insert_position = idx + 1
        else:
            break

    chapter.insert(insert_position, sect1)
    logger.info(f"Wrapped {len(pre_section_elements)} elements in sect1 for chapter {chapter.get('id')}")

    return 1


def fix_chapter_file(xml_path: Path) -> dict:
    """
    Fix a single chapter XML file.

    Returns:
        Dictionary with fix statistics
    """
    stats = {
        'wrapped_in_sect1': 0,
        'nested_para_fixes': 0,
        'empty_row_fixes': 0,
        'total_fixes': 0
    }

    try:
        # Parse XML
        parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
        tree = etree.parse(str(xml_path), parser)
        root = tree.getroot()

        # Apply fixes
        if _local_name(root) == "chapter":
            stats['wrapped_in_sect1'] = wrap_chapter_content_in_sect1(root)

        stats['nested_para_fixes'] = fix_nested_para_elements(root)
        stats['empty_row_fixes'] = fix_empty_table_rows(root)
        stats['total_fixes'] = (stats['wrapped_in_sect1'] +
                               stats['nested_para_fixes'] +
                               stats['empty_row_fixes'])

        # Write back if fixes were made
        if stats['total_fixes'] > 0:
            xml_path.write_bytes(
                etree.tostring(root, encoding="UTF-8", pretty_print=True, xml_declaration=False)
            )
            logger.info(f"Fixed {xml_path.name}: {stats['total_fixes']} total fixes")

        return stats

    except Exception as e:
        logger.error(f"Error processing {xml_path}: {e}")
        return stats


def fix_zip_package(zip_path: Path, output_path: Path = None) -> dict:
    """
    Fix all chapter files in a ZIP package.

    Args:
        zip_path: Path to input ZIP file
        output_path: Path for output ZIP (default: overwrite input)

    Returns:
        Dictionary with overall statistics
    """
    if output_path is None:
        output_path = zip_path

    overall_stats = {
        'files_processed': 0,
        'files_fixed': 0,
        'wrapped_in_sect1': 0,
        'nested_para_fixes': 0,
        'empty_row_fixes': 0,
        'total_fixes': 0
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Extract ZIP
        logger.info(f"Extracting {zip_path}...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        # Find and fix all chapter XML files
        chapter_files = sorted(extract_dir.glob("ch*.xml"))
        logger.info(f"Found {len(chapter_files)} chapter files to process")

        for chapter_file in chapter_files:
            stats = fix_chapter_file(chapter_file)
            overall_stats['files_processed'] += 1

            if stats['total_fixes'] > 0:
                overall_stats['files_fixed'] += 1
                overall_stats['wrapped_in_sect1'] += stats['wrapped_in_sect1']
                overall_stats['nested_para_fixes'] += stats['nested_para_fixes']
                overall_stats['empty_row_fixes'] += stats['empty_row_fixes']
                overall_stats['total_fixes'] += stats['total_fixes']

        # Recreate ZIP with fixed files
        logger.info(f"Creating fixed ZIP: {output_path}...")
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in extract_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(extract_dir)
                    zf.write(file_path, arcname)

    return overall_stats


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix DTD validation violations in RittDoc chapter XML files"
    )
    parser.add_argument(
        "input",
        help="Input ZIP package or XML file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path (default: overwrite input)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    # Process based on file type
    if input_path.suffix.lower() == '.zip':
        stats = fix_zip_package(input_path, output_path)

        print("\n" + "=" * 70)
        print("FIX SUMMARY")
        print("=" * 70)
        print(f"Files processed:        {stats['files_processed']}")
        print(f"Files fixed:            {stats['files_fixed']}")
        print(f"Sect1 wrappers created: {stats['wrapped_in_sect1']}")
        print(f"Nested para fixes:      {stats['nested_para_fixes']}")
        print(f"Empty row fixes:        {stats['empty_row_fixes']}")
        print(f"Total fixes:            {stats['total_fixes']}")
        print("=" * 70)

    else:
        # Single XML file
        stats = fix_chapter_file(input_path)

        print("\n" + "=" * 70)
        print("FIX SUMMARY")
        print("=" * 70)
        print(f"Sect1 wrappers created: {stats['wrapped_in_sect1']}")
        print(f"Nested para fixes:      {stats['nested_para_fixes']}")
        print(f"Empty row fixes:        {stats['empty_row_fixes']}")
        print(f"Total fixes:            {stats['total_fixes']}")
        print("=" * 70)


if __name__ == "__main__":
    main()
