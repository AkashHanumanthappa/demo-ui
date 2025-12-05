#!/usr/bin/env python3
"""
Master PDF to DocBook Integration Script

Complete workflow:
1. Process PDF text with column detection and reading order
2. Extract media (images, tables, vectors)
3. Merge text and media with overlap removal
4. Generate unified hierarchical XML with page number IDs
5. Auto-derive font roles from unified XML
6. Apply heuristics to create structured DocBook XML
7. Package DocBook XML into deliverable ZIP
8. Run RittDoc validation and create compliant package with validation report

This is the single entry point for the entire PDF → DocBook pipeline.

Usage:
    # Basic (Phase 1 only - unified XML)
    python pdf_to_unified_xml.py document.pdf

    # Full pipeline with validation
    python pdf_to_unified_xml.py document.pdf --full-pipeline

    # Full pipeline without validation
    python pdf_to_unified_xml.py document.pdf --full-pipeline --skip-validation
"""

import os
import sys
import argparse
import re
import json
import subprocess
import xml.etree.ElementTree as ET
import gc
from typing import Dict, List, Any, Tuple, Optional
from itertools import groupby
from pathlib import Path

# Import our processing modules
from pdf_to_excel_columns import pdf_to_excel_with_columns
from Multipage_Image_Extractor import extract_media_and_tables

# Import reference mapper for tracking image transformations
try:
    from reference_mapper import get_mapper, reset_mapper
    HAS_REFERENCE_MAPPER = True
except ImportError:
    HAS_REFERENCE_MAPPER = False
    print("Warning: reference_mapper not available - image tracking will be limited")

# Import validation pipeline (for --full-pipeline with validation)
try:
    from rittdoc_compliance_pipeline import RittDocCompliancePipeline
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False


def is_page_number_text(text: str) -> bool:
    """
    Check if text is a page number (roman or arabic numeral only).

    Args:
        text: Text content to check

    Returns:
        True if text is a standalone page number
    """
    text = text.strip()

    # Arabic numerals (1-9999)
    if re.match(r'^\d{1,4}$', text):
        return True

    # Roman numerals (case insensitive)
    if re.match(r'^[ivxlcdm]+$', text, re.IGNORECASE):
        return True

    return False


def extract_page_number(
    fragments: List[Dict[str, Any]],
    page_height: float,
    margin_threshold: float = 150.0
) -> str:
    """
    Extract page number from text fragments at top or bottom of page.

    Strategy:
    - Look for isolated numbers (arabic or roman) near top or bottom margins
    - Page numbers are typically within 150px of top/bottom edge
    - They are usually short standalone text fragments

    Args:
        fragments: List of text fragments on the page
        page_height: Height of the page
        margin_threshold: Distance from top/bottom to search (default: 150px)

    Returns:
        Page number string if found, empty string otherwise
    """
    # Look for page numbers at bottom of page first (most common)
    bottom_candidates = []
    top_candidates = []

    for f in fragments:
        text = f.get("text", "").strip()

        # Skip if not a potential page number
        if not is_page_number_text(text):
            continue

        # Check if at bottom margin
        fragment_bottom = f["top"] + f["height"]
        if fragment_bottom >= page_height - margin_threshold:
            bottom_candidates.append((fragment_bottom, text))

        # Check if at top margin
        fragment_top = f["top"]
        if fragment_top <= margin_threshold:
            top_candidates.append((fragment_top, text))

    # Prefer bottom page numbers (most common convention)
    if bottom_candidates:
        # Return the lowest (closest to bottom) candidate
        bottom_candidates.sort(reverse=True)
        return bottom_candidates[0][1]

    # Fallback to top page numbers
    if top_candidates:
        # Return the highest (closest to top) candidate
        top_candidates.sort()
        return top_candidates[0][1]

    return ""


def point_in_rect(x: float, y: float, x1: float, y1: float, x2: float, y2: float) -> bool:
    """Check if point (x, y) is inside rectangle."""
    return x1 <= x <= x2 and y1 <= y <= y2


def rect_fully_contains_rect(
    inner_x1: float, inner_y1: float, inner_x2: float, inner_y2: float,
    outer_x1: float, outer_y1: float, outer_x2: float, outer_y2: float,
) -> bool:
    """Check if inner rectangle is fully contained within outer rectangle."""
    return (
        outer_x1 <= inner_x1 and
        outer_y1 <= inner_y1 and
        inner_x2 <= outer_x2 and
        inner_y2 <= outer_y2
    )


def fragment_fully_within_bbox(fragment: Dict[str, Any], bbox: Tuple[float, float, float, float]) -> bool:
    """
    Check if text fragment is ENTIRELY within a bounding box.

    Args:
        fragment: Text fragment with 'left', 'top', 'width', 'height'
        bbox: (x1, y1, x2, y2) bounding box

    Returns:
        True if entire fragment is inside bbox
    """
    frag_x1 = fragment["left"]
    frag_y1 = fragment["top"]
    frag_x2 = frag_x1 + fragment["width"]
    frag_y2 = frag_y1 + fragment["height"]

    bbox_x1, bbox_y1, bbox_x2, bbox_y2 = bbox
    return rect_fully_contains_rect(frag_x1, frag_y1, frag_x2, frag_y2, bbox_x1, bbox_y1, bbox_x2, bbox_y2)


def transform_fragment_to_media_coords(
    fragment: Dict[str, Any],
    html_page_width: float,
    html_page_height: float,
    media_page_width: float,
    media_page_height: float,
) -> Dict[str, float]:
    """
    Transform fragment coordinates from pdftohtml space to media.xml space.

    pdftohtml.xml uses scaled HTML coordinates (e.g., 823x1161)
    media.xml uses PyMuPDF/fitz coordinates (e.g., 549x774)

    Both use top-left origin, so only scaling is needed (no Y-flip).

    Args:
        fragment: Text fragment with 'left', 'top', 'width', 'height' in HTML coords
        html_page_width: Page width from pdftohtml.xml
        html_page_height: Page height from pdftohtml.xml
        media_page_width: Page width from media.xml
        media_page_height: Page height from media.xml

    Returns:
        Dict with 'left', 'top', 'width', 'height' in media.xml coordinates
    """
    if html_page_width <= 0 or html_page_height <= 0:
        return fragment  # Fallback to original if invalid

    scale_x = media_page_width / html_page_width
    scale_y = media_page_height / html_page_height

    return {
        "left": fragment["left"] * scale_x,
        "top": fragment["top"] * scale_y,
        "width": fragment["width"] * scale_x,
        "height": fragment["height"] * scale_y,
    }


def transform_media_coords_to_html(
    media_elem: ET.Element,
    media_page_width: float,
    media_page_height: float,
    html_page_width: float,
    html_page_height: float,
) -> None:
    """
    Transform media/table element coordinates from PyMuPDF space to HTML space IN-PLACE.
    
    This ensures all coordinates in unified.xml are in the same coordinate system as text.
    
    PyMuPDF (media.xml) uses PDF points (e.g., 595x842)
    pdftohtml uses HTML coordinates (e.g., 823x1161)
    
    Both use top-left origin, so only scaling is needed.
    
    Args:
        media_elem: ET.Element with x1, y1, x2, y2 attributes in PyMuPDF coords
        media_page_width: Page width from media.xml (PyMuPDF)
        media_page_height: Page height from media.xml (PyMuPDF)
        html_page_width: Page width from pdftohtml.xml (HTML)
        html_page_height: Page height from pdftohtml.xml (HTML)
    """
    if media_page_width <= 0 or media_page_height <= 0:
        return  # No transformation if invalid dimensions
    
    scale_x = html_page_width / media_page_width
    scale_y = html_page_height / media_page_height
    
    # Transform x1, y1, x2, y2 coordinates
    for coord_attr in ['x1', 'y1', 'x2', 'y2']:
        if coord_attr in media_elem.attrib:
            original_val = float(media_elem.get(coord_attr, '0'))
            if coord_attr in ['x1', 'x2']:
                transformed_val = original_val * scale_x
            else:  # y1, y2
                transformed_val = original_val * scale_y
            media_elem.set(coord_attr, f"{transformed_val:.2f}")
    
    # Transform table cell coordinates if this is a table
    if media_elem.tag == 'table':
        rows_elem = media_elem.find('rows')
        if rows_elem is not None:
            for row_elem in rows_elem.findall('row'):
                for cell_elem in row_elem.findall('cell'):
                    for coord_attr in ['x1', 'y1', 'x2', 'y2']:
                        if coord_attr in cell_elem.attrib:
                            original_val = float(cell_elem.get(coord_attr, '0'))
                            if coord_attr in ['x1', 'x2']:
                                transformed_val = original_val * scale_x
                            else:
                                transformed_val = original_val * scale_y
                            cell_elem.set(coord_attr, f"{transformed_val:.2f}")


def fragment_overlaps_media(fragment: Dict[str, Any], media_bbox: Tuple[float, float, float, float]) -> bool:
    """
    Check if text fragment's center overlaps with media bounding box.

    NOTE: This is used for non-table media (images, vectors).
    For tables, use fragment_overlaps_table_cells() instead.

    Args:
        fragment: Text fragment with 'left', 'top', 'width', 'height'
        media_bbox: (x1, y1, x2, y2) bounding box

    Returns:
        True if fragment center is inside media bbox
    """
    # Calculate fragment center
    center_x = fragment["left"] + fragment["width"] / 2.0
    center_y = fragment["top"] + fragment["height"] / 2.0

    x1, y1, x2, y2 = media_bbox
    return point_in_rect(center_x, center_y, x1, y1, x2, y2)


def parse_media_xml(media_xml_path: str) -> Dict[int, Dict[str, Any]]:
    """
    Parse the multimedia XML and organize by page.

    Returns:
        {page_number: {"media": [...], "tables": [...], "page_width": float, "page_height": float}}
    """
    if not os.path.exists(media_xml_path):
        return {}

    tree = ET.parse(media_xml_path)
    root = tree.getroot()

    pages_media = {}

    for page_elem in root.findall("page"):
        page_num = int(page_elem.get("index", "0"))

        media_elements = page_elem.findall("media")
        table_elements = page_elem.findall("table")

        # Extract page dimensions from media.xml for coordinate transformation
        media_page_width = float(page_elem.get("width", "0"))
        media_page_height = float(page_elem.get("height", "0"))

        pages_media[page_num] = {
            "media": media_elements,
            "tables": table_elements,
            "page_width": media_page_width,
            "page_height": media_page_height,
        }

    return pages_media


def find_caption_for_image(
    image_bbox: Tuple[float, float, float, float],
    fragments: List[Dict[str, Any]],
    page_height: float,
) -> str:
    """
    Find caption text near an image using spatial proximity and pattern matching.

    Strategy:
    - Look for text fragments near the image (within 100 pixels above/below)
    - Match patterns like "Figure X.Y", "Fig. X.Y", "Fig X.Y", etc.
    - Return the matched caption text or empty string

    Args:
        image_bbox: (x1, y1, x2, y2) bounding box of image
        fragments: List of text fragments on the same page
        page_height: Height of the page for coordinate normalization

    Returns:
        Caption text if found, empty string otherwise
    """
    import re

    img_x1, img_y1, img_x2, img_y2 = image_bbox
    img_center_y = (img_y1 + img_y2) / 2

    # Pattern to match figure captions
    # Matches: "Figure 1.1", "Fig. 1.2", "Fig 1.3", "  Figure 1.4", etc.
    # Also matches text containing "Figure X.Y" anywhere in the string
    caption_pattern = re.compile(r'Fig(?:ure)?\.?\s+\d+\.\d+', re.IGNORECASE)

    # Search for caption within 600 pixels above or below the image center
    # Large radius needed since some images are full-page or far from captions
    search_radius = 600.0
    candidates = []

    for f in fragments:
        frag_y = f["top"] + f["height"] / 2  # Fragment center Y
        distance = abs(frag_y - img_center_y)

        if distance <= search_radius:
            text = f.get("text", "").strip()
            if caption_pattern.search(text):  # Use search instead of match to find pattern anywhere
                candidates.append((distance, text, f))

    # Return the closest matching caption
    if candidates:
        candidates.sort(key=lambda x: x[0])  # Sort by distance
        _, caption_text, _ = candidates[0]
        return caption_text

    return ""


def extract_image_caption_associations(
    media_data: Dict[int, Dict[str, List[ET.Element]]],
    text_data: Dict[str, Any],
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Step 1: Pre-Process and Collect Image Data with Captions.

    For each image in MultiMedia.xml:
    - Extract page number, bounding box, XML tag
    - Find caption text by searching nearby text fragments
    - Store as structured data for later insertion

    Returns:
        {page_num: [{"bbox": (x1,y1,x2,y2), "element": ET.Element, "caption": "..."}]}
    """
    image_data = {}

    for page_num, media_info in media_data.items():
        if page_num not in text_data["pages"]:
            continue

        page_info = text_data["pages"][page_num]
        fragments = page_info["fragments"]
        page_height = page_info["page_height"]

        page_images = []

        for media_elem in media_info.get("media", []):
            bbox = get_element_bbox(media_elem)
            caption = find_caption_for_image(bbox, fragments, page_height)

            page_images.append({
                "bbox": bbox,
                "element": media_elem,
                "caption": caption,
            })

            if caption:
                print(f"  Page {page_num}: Found caption '{caption}' for image {media_elem.get('id', 'unknown')}")

        if page_images:
            image_data[page_num] = page_images

    return image_data


def get_element_bbox(elem: ET.Element) -> Tuple[float, float, float, float]:
    """Extract bounding box from media or table element."""
    x1 = float(elem.get("x1", "0"))
    y1 = float(elem.get("y1", "0"))
    x2 = float(elem.get("x2", "0"))
    y2 = float(elem.get("y2", "0"))
    return (x1, y1, x2, y2)


def get_element_top(elem: ET.Element) -> float:
    """Get the top Y coordinate of an element."""
    return float(elem.get("y1", "0"))


def extract_table_cell_bboxes(table_elem: ET.Element) -> List[Tuple[float, float, float, float]]:
    """
    Extract all cell bounding boxes from a table element.

    Args:
        table_elem: <table> element with <rows><row><cell> structure

    Returns:
        List of (x1, y1, x2, y2) tuples for each cell
    """
    cell_bboxes = []

    rows_elem = table_elem.find("rows")
    if rows_elem is None:
        return cell_bboxes

    for row_elem in rows_elem.findall("row"):
        for cell_elem in row_elem.findall("cell"):
            x1 = float(cell_elem.get("x1", "0"))
            y1 = float(cell_elem.get("y1", "0"))
            x2 = float(cell_elem.get("x2", "0"))
            y2 = float(cell_elem.get("y2", "0"))
            cell_bboxes.append((x1, y1, x2, y2))

    return cell_bboxes


def fragment_overlaps_table_cells(
    fragment: Dict[str, Any],
    table_cell_bboxes: List[Tuple[float, float, float, float]],
) -> bool:
    """
    Check if a text fragment's CENTER is within any table cell.

    Uses center-point detection (same as media overlap) for consistency:
    - If the fragment's center falls within a cell, mark it as overlapping
    - This is more lenient than requiring full containment

    Args:
        fragment: Text fragment with 'left', 'top', 'width', 'height'
        table_cell_bboxes: List of (x1, y1, x2, y2) cell bounding boxes

    Returns:
        True if fragment center is inside any cell
    """
    # Calculate fragment center
    center_x = fragment["left"] + fragment["width"] / 2.0
    center_y = fragment["top"] + fragment["height"] / 2.0

    for cell_bbox in table_cell_bboxes:
        x1, y1, x2, y2 = cell_bbox
        if point_in_rect(center_x, center_y, x1, y1, x2, y2):
            return True
    return False


def get_fragment_table_cell_id(
    fragment: Dict[str, Any],
    table_cell_info: List[Tuple[str, Tuple[float, float, float, float]]],
) -> str:
    """
    Get the unique cell ID for a fragment if its center is within a table cell.

    Uses center-point detection for consistency with overlap detection.

    Args:
        fragment: Text fragment with 'left', 'top', 'width', 'height'
        table_cell_info: List of (cell_id, (x1, y1, x2, y2)) tuples

    Returns:
        Cell ID if fragment center is within a cell, empty string otherwise
    """
    # Calculate fragment center
    center_x = fragment["left"] + fragment["width"] / 2.0
    center_y = fragment["top"] + fragment["height"] / 2.0

    for cell_id, cell_bbox in table_cell_info:
        x1, y1, x2, y2 = cell_bbox
        if point_in_rect(center_x, center_y, x1, y1, x2, y2):
            return cell_id
    return ""


def assign_reading_order_to_media(
    media_elements: List[ET.Element],
    fragments: List[Dict[str, Any]],
    media_page_width: float = 0.0,
    media_page_height: float = 0.0,
    html_page_width: float = 0.0,
    html_page_height: float = 0.0,
) -> List[Tuple[ET.Element, float, int]]:
    """
    Assign reading order positions to media elements based on vertical position.
    
    CRITICAL: Transforms media coordinates from PyMuPDF space to HTML space before comparison.
    This ensures media elements are positioned correctly relative to text.

    Args:
        media_elements: List of media/table elements with x1,y1,x2,y2 in PyMuPDF coords
        fragments: Text fragments with top,left,width,height in HTML coords
        media_page_width: Page width in PyMuPDF coordinates (for transformation)
        media_page_height: Page height in PyMuPDF coordinates (for transformation)
        html_page_width: Page width in HTML coordinates (for transformation)
        html_page_height: Page height in HTML coordinates (for transformation)

    Returns:
        List of (element, reading_order_index, reading_block) tuples
    """
    result = []
    
    # Calculate coordinate transformation scale
    has_valid_coords = (media_page_width > 0 and media_page_height > 0 and 
                       html_page_width > 0 and html_page_height > 0)
    scale_y = html_page_height / media_page_height if has_valid_coords else 1.0

    for elem in media_elements:
        elem_top_pymupdf = get_element_top(elem)  # PyMuPDF coordinates
        
        # Transform to HTML space to match fragment coordinates
        elem_top = elem_top_pymupdf * scale_y if has_valid_coords else elem_top_pymupdf
        
        # Debug: Log transformation for first few elements
        if len(result) < 3 and has_valid_coords:
            elem_id = elem.get('id', 'unknown')
            # Uncomment for debugging:
            # print(f"    Media {elem_id}: PyMuPDF top={elem_top_pymupdf:.1f} → HTML top={elem_top:.1f} (scale={scale_y:.3f})")

        # Find fragments before and after this element vertically
        before = [f for f in fragments if f["top"] < elem_top]

        if not before:
            # Media is before all text
            reading_order = 0.5
            reading_block = 1
        else:
            # Find the last fragment before this media
            last_before = max(before, key=lambda f: f["reading_order_index"])
            reading_order = last_before["reading_order_index"] + 0.5
            reading_block = last_before["reading_order_block"]

        result.append((elem, reading_order, reading_block))

    return result


def merge_text_and_media_simple(
    text_data: Dict[str, Any],
    media_data: Dict[int, Dict[str, List[ET.Element]]],
) -> Dict[int, Dict[str, Any]]:
    """
    Merge text fragments and media elements using simple bbox-based positioning.

    Strategy:
    1. Remove text that's INSIDE table cells (tables already contain the text)
    2. Remove text that's INSIDE image/vector bounding boxes (avoid duplication)
    3. Insert images and tables based on their bbox reading order
    4. No caption matching needed - pure spatial positioning
    5. CRITICAL: Also process pages with ONLY media (no text)

    This ensures:
    - No duplicate content from text overlapping images/tables
    - Images and tables are correctly positioned by bbox
    - Image-only pages are not skipped

    Returns:
        {page_num: {"fragments": [...], "tables": [...], "media": [...]}}
    """
    merged_pages = {}

    # CRITICAL FIX: Get all page numbers from BOTH text and media
    # Pages with only images (no text) were being skipped!
    all_page_nums = set(text_data["pages"].keys()) | set(media_data.keys())
    
    for page_num in sorted(all_page_nums):
        # Check if page has text data
        page_info = text_data["pages"].get(page_num)
        
        # Get media for this page first (needed for both text and image-only pages)
        media_list = []
        table_list = []
        media_page_width = 0.0
        media_page_height = 0.0

        if page_num in media_data:
            media_list = media_data[page_num].get("media", [])
            table_list = media_data[page_num].get("tables", [])
            media_page_width = media_data[page_num].get("page_width", 0.0)
            media_page_height = media_data[page_num].get("page_height", 0.0)
        
        # Now handle text vs. image-only pages
        if page_info:
            # Page has text - process normally
            fragments = page_info["fragments"]
            page_width = page_info["page_width"]   # HTML/pdftohtml coordinates (e.g., 823)
            page_height = page_info["page_height"]  # HTML/pdftohtml coordinates (e.g., 1161)
        else:
            # Page has NO text (image-only page) - estimate HTML dimensions from media
            fragments = []
            
            # Convert PyMuPDF dimensions to HTML dimensions
            # Typical scale factor is ~1.5 (PDF points to HTML pixels)
            # Common conversions: 549→823, 774→1161, 595→892, 842→1263
            if media_page_width > 0 and media_page_height > 0:
                scale_factor = 1.5  # Approximate scale factor
                page_width = media_page_width * scale_factor
                page_height = media_page_height * scale_factor
                print(f"  ⚠ Page {page_num}: No text (image-only page), using estimated dimensions {page_width:.0f}x{page_height:.0f}")
            else:
                # Fallback to common page size
                page_width = 823.0
                page_height = 1161.0
                print(f"  ⚠ Page {page_num}: No text and no media dimensions, using default 823x1161")

        # ========== STEP A: Build bounding boxes for tables and media ==========

        # Build a list of (cell_id, bbox) for all table cells on this page
        all_table_cell_info = []
        for table_idx, table_elem in enumerate(table_list):
            table_id = table_elem.get("id", f"table_{table_idx}")
            rows_elem = table_elem.find("rows")
            if rows_elem is None:
                continue

            for row_elem in rows_elem.findall("row"):
                row_idx = row_elem.get("index", "0")
                for cell_elem in row_elem.findall("cell"):
                    cell_idx = cell_elem.get("index", "0")
                    x1 = float(cell_elem.get("x1", "0"))
                    y1 = float(cell_elem.get("y1", "0"))
                    x2 = float(cell_elem.get("x2", "0"))
                    y2 = float(cell_elem.get("y2", "0"))
                    cell_bbox = (x1, y1, x2, y2)
                    # Create unique cell ID: "table_id:row:col"
                    cell_id = f"{table_id}:r{row_idx}:c{cell_idx}"
                    all_table_cell_info.append((cell_id, cell_bbox))

        # Extract just the bboxes for the overlap check
        all_table_cell_bboxes = [bbox for _, bbox in all_table_cell_info]

        # Build list of media bounding boxes (images, vectors)
        all_media_bboxes = []
        for media_elem in media_list:
            bbox = get_element_bbox(media_elem)
            if bbox:
                all_media_bboxes.append(bbox)

        # ========== STEP B: Filter text inside tables and media ==========
        filtered_fragments = []
        removed_by_tables = 0
        removed_by_media = 0

        # Check if we have valid media dimensions for coordinate transformation
        has_valid_media_coords = media_page_width > 0 and media_page_height > 0

        for f in fragments:
            # CRITICAL: Add page number to fragment for paragraph boundary detection
            f["page_num"] = page_num

            # Transform fragment coordinates to media.xml space for overlap checks
            if has_valid_media_coords:
                f_transformed = transform_fragment_to_media_coords(
                    f, page_width, page_height, media_page_width, media_page_height
                )
            else:
                f_transformed = f  # Fallback to original coords if no media dimensions

            # Assign cell ID if fragment is inside a table cell (using transformed coords)
            cell_id = get_fragment_table_cell_id(f_transformed, all_table_cell_info)
            f["table_cell_id"] = cell_id

            # Remove text if it's ENTIRELY within a table cell (using transformed coords)
            if fragment_overlaps_table_cells(f_transformed, all_table_cell_bboxes):
                removed_by_tables += 1
                continue

            # Remove text if it's inside an image/vector bounding box (using transformed coords)
            inside_media = False
            for media_bbox in all_media_bboxes:
                if fragment_overlaps_media(f_transformed, media_bbox):
                    inside_media = True
                    break

            if inside_media:
                removed_by_media += 1
                continue

            filtered_fragments.append(f)

        # Log filtering statistics
        if removed_by_tables > 0 or removed_by_media > 0:
            print(f"  Page {page_num}: Removed {removed_by_tables} fragments inside tables, "
                  f"{removed_by_media} inside images, kept {len(filtered_fragments)}")

        # Assign reading order to media and tables based on bbox
        # Pass dimensions for coordinate transformation (PyMuPDF → HTML space)
        media_with_order = assign_reading_order_to_media(
            media_list, 
            filtered_fragments,
            media_page_width,
            media_page_height,
            page_width,
            page_height
        )
        tables_with_order = assign_reading_order_to_media(
            table_list, 
            filtered_fragments,
            media_page_width,
            media_page_height,
            page_width,
            page_height
        )

        merged_pages[page_num] = {
            "page_width": page_width,
            "page_height": page_height,
            "media_page_width": media_page_width,  # Store for coordinate transformation
            "media_page_height": media_page_height,  # Store for coordinate transformation
            "fragments": filtered_fragments,
            "media": media_with_order,
            "tables": tables_with_order,
            "page_number_fragments": page_info.get("page_number_fragments", []) if page_info else [],  # Handle image-only pages
        }

    return merged_pages


def calculate_column_boundaries(
    fragments: List[Dict[str, Any]],
    page_width: float
) -> Dict[int, Dict[str, float]]:
    """
    Calculate typical left-start and right-end positions for each column.

    Args:
        fragments: All fragments on the page
        page_width: Width of the page

    Returns:
        Dictionary mapping col_id to {left_start, right_end, margin_tolerance}
        where margin_tolerance is used to check if lines are "full width"
    """
    from statistics import median

    # Group fragments by col_id
    col_groups = {}
    for f in fragments:
        col_id = f["col_id"]
        if col_id not in col_groups:
            col_groups[col_id] = []
        col_groups[col_id].append(f)

    # Calculate boundaries for each column
    boundaries = {}
    for col_id, frags in col_groups.items():
        if not frags:
            continue

        # Get all left positions and right positions
        left_positions = [f["left"] for f in frags]
        right_positions = [f["left"] + f["width"] for f in frags]

        # Use median for robustness (handles outliers better than mean)
        typical_left = median(left_positions)
        typical_right = median(right_positions)

        # For col_id 0 (full-width), use page width
        if col_id == 0:
            typical_left = 0
            typical_right = page_width

        # Calculate tolerance based on column width
        col_width = typical_right - typical_left
        # Use 10% of column width or 20 pixels, whichever is smaller
        tolerance = min(col_width * 0.10, 20.0)

        boundaries[col_id] = {
            "left_start": typical_left,
            "right_end": typical_right,
            "tolerance": tolerance
        }

    return boundaries


def is_paragraph_break(
    prev_fragment: Dict[str, Any],
    curr_fragment: Dict[str, Any],
    typical_line_height: float,
    column_boundaries: Dict[int, Dict[str, float]] = None,
) -> bool:
    """
    Determine if there should be a paragraph break between two fragments.

    Paragraph breaks occur when:
    1. Table cell ID changes (different table cells)
    2. Column ID changes (different columns)
    3. Reading block changes (transitions between full-width and columns)
    4. Vertical gap is NOT zero, negative, or very small
       - Combine when gap <= 3 pixels (continuous text flow)
       - Break when gap > 3 pixels (indicates paragraph separation)
    5. Current line doesn't extend to full width AND next line doesn't start at left
       - Only merge if current line is "full width" AND next line starts at "left edge"

    Args:
        prev_fragment: Previous text fragment
        curr_fragment: Current text fragment
        typical_line_height: Median line height for the page
        column_boundaries: Optional dict with column boundary information

    Returns:
        True if a paragraph break should occur
    """
    # Break if table_cell_id changes (different table cells)
    # CRITICAL: Never merge text across cell boundaries, even if same ColID/ReadingBlock
    prev_cell_id = prev_fragment.get("table_cell_id", "")
    curr_cell_id = curr_fragment.get("table_cell_id", "")

    # If either fragment has a cell ID, check if they're in the same cell
    if prev_cell_id or curr_cell_id:
        if prev_cell_id != curr_cell_id:
            return True

    # Break if col_id changes (different columns or full-width vs column)
    if prev_fragment["col_id"] != curr_fragment["col_id"]:
        return True

    # Break if reading_block changes (major content sections)
    # Note: This is redundant when processing within reading blocks, but kept for safety
    if prev_fragment["reading_order_block"] != curr_fragment["reading_order_block"]:
        return True

    # Calculate vertical gap between fragments
    prev_bottom = prev_fragment["top"] + prev_fragment["height"]
    curr_top = curr_fragment["top"]
    vertical_gap = curr_top - prev_bottom

    # Combine fragments when vertical gap is:
    # - Zero or negative (overlapping or touching)
    # - Very small (<= 3 pixels) indicating continuous text flow
    # Break otherwise (gap > 3 pixels indicates paragraph separation)
    SMALL_GAP_THRESHOLD = 3.0  # pixels
    if vertical_gap > SMALL_GAP_THRESHOLD:
        return True

    # Additional check: Only merge if BOTH lines are full-width:
    # - Previous line extends to full width (reaches right edge)
    # - Current line starts at left edge AND extends to right edge
    if column_boundaries:
        col_id = prev_fragment["col_id"]
        if col_id in column_boundaries:
            boundaries = column_boundaries[col_id]
            tolerance = boundaries["tolerance"]

            # Check if previous line extends close to right edge
            prev_right = prev_fragment["left"] + prev_fragment["width"]
            prev_extends_to_right = abs(prev_right - boundaries["right_end"]) <= tolerance

            # Check if current line starts close to left edge
            curr_left = curr_fragment["left"]
            curr_starts_at_left = abs(curr_left - boundaries["left_start"]) <= tolerance

            # Check if current line extends close to right edge
            curr_right = curr_fragment["left"] + curr_fragment["width"]
            curr_extends_to_right = abs(curr_right - boundaries["right_end"]) <= tolerance

            # Only merge if ALL conditions are true:
            # - Previous line extends to full width (reaches right edge)
            # - Current line starts at left edge
            # - Current line extends to full width (reaches right edge)
            if not (prev_extends_to_right and curr_starts_at_left and curr_extends_to_right):
                return True  # Break paragraph if conditions not met

    return False


def get_fragment_font_attrs(fragment: Dict[str, Any], original_texts: Dict[Tuple[int, int], ET.Element]) -> Dict[str, Any]:
    """
    Extract font attributes (font ID, size, bold, italic) from fragment.
    
    Args:
        fragment: Text fragment dictionary
        original_texts: Lookup dictionary for original pdftohtml elements
    
    Returns:
        Dictionary with font, size, bold, italic information
    """
    page_num = fragment.get("page_num", fragment.get("page", None))
    stream_index = fragment.get("stream_index")
    
    # Default values
    attrs = {
        "font": None,
        "size": 12.0,  # Default font size
        "bold": False,
        "italic": False,
    }
    
    # Look up original element
    if page_num is not None and stream_index is not None:
        orig_elem = original_texts.get((page_num, stream_index))
        if orig_elem is not None:
            # Extract font ID
            attrs["font"] = orig_elem.get("font")
            
            # Extract size
            size_str = orig_elem.get("size", "12")
            try:
                attrs["size"] = float(size_str)
            except (ValueError, TypeError):
                attrs["size"] = 12.0
    
    # Check for bold/italic in inner_xml
    inner_xml = fragment.get("inner_xml", "")
    attrs["bold"] = "<b>" in inner_xml or "<strong>" in inner_xml
    attrs["italic"] = "<i>" in inner_xml or "<em>" in inner_xml
    
    return attrs


def is_bullet_text(text: str) -> bool:
    """
    Check if text is a bullet point character or starts with bullet pattern.
    
    Detects:
    - Single bullet characters: •, ●, ○, ■, □, ▪, ▫, ·, -, *, –, —
    - Numbered lists: 1., 2., 3., or (1), (2), (3)
    - Lettered lists: a., b., c., or (a), (b), (c)
    """
    import re
    
    text = text.strip()
    if not text:
        return False
    
    # Single bullet characters
    BULLET_CHARS = {'•', '●', '○', '■', '□', '▪', '▫', '·', '-', '*', '–', '—', '→', '⇒', '▸', '►'}
    if text in BULLET_CHARS:
        return True
    
    # Bullet patterns (at start of text)
    BULLET_PATTERNS = [
        r'^[•●○■□▪▫·\-\*–—→⇒▸►]\s+',  # Bullet + space
        r'^\d+[\.\)]\s+',               # 1. or 1) followed by space
        r'^[a-zA-Z][\.\)]\s+',          # a. or a) followed by space
        r'^\([0-9]+\)\s+',              # (1) followed by space
        r'^\([a-zA-Z]\)\s+',            # (a) followed by space
        r'^[ivxlcdm]+[\.\)]\s+',        # Roman numerals: i., ii., iii.
    ]
    
    for pattern in BULLET_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    
    return False


def should_merge_fragments(prev_fragment: Dict[str, Any], curr_fragment: Dict[str, Any], baseline_tolerance: float = 3.0) -> bool:
    """
    Determine if two fragments should be merged into the same paragraph.

    Only merge if:
    1. They're on the same baseline (same line) within tolerance
    2. AND there's evidence of word continuation:
       - Previous text ends with space, OR
       - Current text starts with space, OR
       - Previous text ends with hyphen (word break)

    This is a simplified approach that avoids complex paragraph detection
    which fails in TOC, Index, and other structured content.

    Args:
        prev_fragment: Previous text fragment
        curr_fragment: Current text fragment
        baseline_tolerance: Max difference in baseline to consider same line

    Returns:
        True if fragments should be merged
    """
    # Check if on same baseline (same line)
    baseline_diff = abs(prev_fragment["baseline"] - curr_fragment["baseline"])
    if baseline_diff > baseline_tolerance:
        return False

    # Must be same column and reading block
    if prev_fragment["col_id"] != curr_fragment["col_id"]:
        return False
    if prev_fragment["reading_order_block"] != curr_fragment["reading_order_block"]:
        return False

    # Check for space/hyphen evidence of word continuation
    prev_text = prev_fragment.get("text", "")
    curr_text = curr_fragment.get("text", "")

    # Merge if previous ends with space
    if prev_text.endswith(" "):
        return True

    # Merge if current starts with space
    if curr_text.startswith(" "):
        return True

    # Merge if previous ends with hyphen (word break)
    if prev_text.endswith("-"):
        return True

    # No evidence of continuation - don't merge
    return False


def group_fragments_into_paragraphs(
    fragments: List[Dict[str, Any]],
    typical_line_height: float,
    page_num: int = 0,
    debug: bool = False,
    page_width: float = None,
    original_texts: Dict[Tuple[int, int], ET.Element] = None,
) -> List[List[Dict[str, Any]]]:
    """
    Group consecutive fragments into paragraphs with font/style-aware detection.

    Paragraph breaks occur when:
    1. Font changes (different font ID)
    2. Font size changes significantly (>= 2pt difference)
    3. Style changes (bold/italic transitions in some cases)
    4. Vertical gap exceeds adaptive threshold
    5. Different column/reading block/page
    6. Bullet point detection (list items)

    Args:
        fragments: List of text fragments sorted by reading order
        typical_line_height: Median line height for the page
        page_num: Page number for debug logging
        debug: Enable debug logging
        page_width: Width of the page (unused)
        original_texts: Lookup dictionary for original pdftohtml elements (for font info)

    Returns:
        List of paragraph groups (each group is a list of fragments)
    """
    if not fragments:
        return []

    paragraphs = []
    current_paragraph = [fragments[0]]
    
    # Base threshold - will be adaptive based on font size
    base_gap_threshold = typical_line_height * 1.5 if typical_line_height > 0 else 18.0

    for i in range(1, len(fragments)):
        prev_fragment = fragments[i - 1]
        curr_fragment = fragments[i]
        
        # Calculate vertical gap
        prev_bottom = prev_fragment["top"] + prev_fragment["height"]
        curr_top = curr_fragment["top"]
        vertical_gap = curr_top - prev_bottom
        
        # Get font attributes for both fragments
        prev_attrs = get_fragment_font_attrs(prev_fragment, original_texts or {})
        curr_attrs = get_fragment_font_attrs(curr_fragment, original_texts or {})
        
        # Check if current fragment is a bullet point
        curr_text = curr_fragment.get("text", "").strip()
        is_bullet = is_bullet_text(curr_text)
        
        # Decision logic for starting new paragraph
        should_start_new_para = False
        break_reason = ""
        
        # 0. CRITICAL: Different page → always new paragraph
        prev_page = prev_fragment.get("page_num", prev_fragment.get("page", None))
        curr_page = curr_fragment.get("page_num", curr_fragment.get("page", None))
        if prev_page is not None and curr_page is not None and prev_page != curr_page:
            should_start_new_para = True
            break_reason = f"page boundary: {prev_page} → {curr_page}"
        
        # 1. Different column or reading block → new paragraph
        elif (prev_fragment["col_id"] != curr_fragment["col_id"] or
            prev_fragment["reading_order_block"] != curr_fragment["reading_order_block"]):
            should_start_new_para = True
            break_reason = "col/block change"
        
        # 2. NEW: Font change → new paragraph (different font family)
        elif prev_attrs["font"] and curr_attrs["font"] and prev_attrs["font"] != curr_attrs["font"]:
            should_start_new_para = True
            break_reason = f"font change: {prev_attrs['font']} → {curr_attrs['font']}"
        
        # 3. NEW: Significant font size change → new paragraph (heading detection)
        elif abs(prev_attrs["size"] - curr_attrs["size"]) >= 2.0:
            should_start_new_para = True
            break_reason = f"size change: {prev_attrs['size']:.1f}pt → {curr_attrs['size']:.1f}pt"
        
        # 4. NEW: Bullet point starts new paragraph (list item)
        elif is_bullet and vertical_gap > 2.0:  # Small gap tolerance for bullets
            should_start_new_para = True
            break_reason = "bullet point"
        
        # 5. NEW: Adaptive vertical gap based on current font size
        # Threshold = 70% of font size (adaptive to heading vs body text)
        adaptive_threshold = max(curr_attrs["size"] * 0.7, base_gap_threshold)
        if vertical_gap > adaptive_threshold:
            should_start_new_para = True
            break_reason = f"large gap={vertical_gap:.1f}px > {adaptive_threshold:.1f}px"
        
        # 6. Same baseline continuation check
        elif should_merge_fragments(prev_fragment, curr_fragment):
            # Same baseline with space/hyphen → continue paragraph
            if debug:
                print(f"      Fragment {i}: Continue para (same line)")
            current_paragraph.append(curr_fragment)
            continue
        
        # 7. Medium gap - check if normal line spacing within same paragraph
        elif vertical_gap > 3.0:
            # Allow continuation if gap is less than font size (normal line spacing)
            if vertical_gap <= curr_attrs["size"]:
                # Normal line spacing for this font size
                if debug:
                    print(f"      Fragment {i}: Continue para (normal line spacing={vertical_gap:.1f}px for size {curr_attrs['size']:.1f}pt)")
                current_paragraph.append(curr_fragment)
                continue
            else:
                # Larger gap, start new paragraph
                should_start_new_para = True
                break_reason = f"medium gap={vertical_gap:.1f}px"
        else:
            # Very small gap (<= 3px), continue paragraph
            if debug:
                print(f"      Fragment {i}: Continue para (small gap={vertical_gap:.1f}px)")
            current_paragraph.append(curr_fragment)
            continue
        
        # Start new paragraph if needed
        if should_start_new_para:
            if debug and break_reason:
                print(f"      Fragment {i}: New para ({break_reason})")
            paragraphs.append(current_paragraph)
            current_paragraph = [curr_fragment]
        else:
            current_paragraph.append(curr_fragment)

    # Add the last paragraph
    if current_paragraph:
        paragraphs.append(current_paragraph)

    if debug:
        print(f"  Page {page_num}: Created {len(paragraphs)} paragraphs from {len(fragments)} fragments")

    return paragraphs


def should_merge_cross_page_paragraphs(
    last_para_fragments: List[Dict[str, Any]],
    first_para_fragments: List[Dict[str, Any]],
    original_texts: Dict[Tuple[int, int], ET.Element],
    debug: bool = False,
) -> Tuple[bool, str]:
    """
    Determine if two paragraphs across a page boundary should be merged.
    
    Paragraphs should merge if:
    1. Same font family and size
    2. Same column and reading block context
    3. Last paragraph doesn't end with sentence terminator (., !, ?, ;, :)
    4. No style break (bold/italic continuity)
    5. Consistent indentation pattern
    
    Args:
        last_para_fragments: Fragments from last paragraph on page N
        first_para_fragments: Fragments from first paragraph on page N+1
        original_texts: Font info lookup
        debug: Enable debug logging
    
    Returns:
        (should_merge: bool, reason: str)
    """
    if not last_para_fragments or not first_para_fragments:
        return False, "empty paragraphs"
    
    # Get last fragment of previous paragraph
    last_frag = last_para_fragments[-1]
    # Get first fragment of next paragraph
    first_frag = first_para_fragments[0]
    
    # Check 1: Must be consecutive pages
    last_page = last_frag.get("page_num", last_frag.get("page"))
    first_page = first_frag.get("page_num", first_frag.get("page"))
    
    if last_page is None or first_page is None:
        return False, "missing page info"
    
    if first_page != last_page + 1:
        return False, f"non-consecutive pages ({last_page} -> {first_page})"
    
    # Check 2: Same column and reading block
    if (last_frag["col_id"] != first_frag["col_id"] or
        last_frag["reading_order_block"] != first_frag["reading_order_block"]):
        return False, "different column/reading block"
    
    # Check 3: Font continuity (family and size)
    last_attrs = get_fragment_font_attrs(last_frag, original_texts)
    first_attrs = get_fragment_font_attrs(first_frag, original_texts)
    
    if last_attrs["font"] != first_attrs["font"]:
        return False, f"font change ({last_attrs['font']} -> {first_attrs['font']})"
    
    if abs(last_attrs["size"] - first_attrs["size"]) >= 2.0:
        return False, f"size change ({last_attrs['size']:.1f}pt -> {first_attrs['size']:.1f}pt)"
    
    # Check 4: Semantic continuity - does last paragraph end with sentence terminator?
    last_text = last_frag.get("text", "").strip()
    
    # Sentence terminators indicate paragraph should NOT continue
    sentence_terminators = {'.', '!', '?', ';', ':', '。', '！', '？'}
    
    # Also check for list/heading patterns that indicate breaks
    heading_patterns = [
        r'^\d+\.',  # "1. Heading"
        r'^[A-Z][a-z]*:$',  # "Chapter:" or "Section:"
        r'^[IVX]+\.',  # "I. Roman numeral"
    ]
    
    if last_text:
        # Check if ends with terminator
        if last_text[-1] in sentence_terminators:
            return False, f"sentence terminator: '{last_text[-1]}'"
        
        # Check if last line looks like a heading/list item
        for pattern in heading_patterns:
            if re.match(pattern, last_text):
                return False, f"heading pattern: {pattern}"
    
    # Check 5: First paragraph shouldn't start like a new section
    first_text = first_frag.get("text", "").strip()
    
    # New paragraph indicators
    new_para_patterns = [
        r'^[A-Z][a-z]+\s+\d+',  # "Chapter 1", "Section 2"
        r'^\d+\.\d+',  # "1.1", "2.3" (subsection)
        r'^[•●○■□▪▫·\-\*]',  # Bullet points
    ]
    
    for pattern in new_para_patterns:
        if re.match(pattern, first_text):
            return False, f"new section pattern: {pattern}"
    
    # Check 6: Style continuity (bold/italic)
    # If significant style change, probably a new paragraph
    if last_attrs.get("bold") != first_attrs.get("bold"):
        # Allow regular -> bold transition if first text looks like emphasis
        # But bold -> regular usually means end of emphasis block
        if last_attrs.get("bold") and not first_attrs.get("bold"):
            return False, "style change: bold -> regular"
    
    # All checks passed - paragraphs should merge
    merge_reason = f"continuous: same font ({last_attrs['font']}), no terminator"
    
    if debug:
        print(f"    Cross-page merge: page {last_page}->{first_page}, {merge_reason}")
    
    return True, merge_reason


def merge_cross_page_paragraphs(
    all_paragraph_data: List[Tuple[int, List[List[Dict[str, Any]]]]],
    original_texts: Dict[Tuple[int, int], ET.Element],
    debug: bool = False,
) -> List[Tuple[int, List[List[Dict[str, Any]]]]]:
    """
    Post-process paragraphs to merge those that span page boundaries.
    
    This is called after all pages have been processed and paragraphs created.
    It scans for consecutive paragraphs across page boundaries and merges them
    if they represent continuous text flow.
    
    Args:
        all_paragraph_data: List of (page_num, paragraphs) tuples
        original_texts: Font info lookup
        debug: Enable debug logging
    
    Returns:
        Updated list of (page_num, paragraphs) with merged cross-page paragraphs
    """
    if not all_paragraph_data:
        return all_paragraph_data
    
    # Sort by page number to ensure correct order
    sorted_data = sorted(all_paragraph_data, key=lambda x: x[0])
    
    merge_count = 0
    
    # Scan through consecutive pages
    for i in range(len(sorted_data) - 1):
        curr_page_num, curr_paragraphs = sorted_data[i]
        next_page_num, next_paragraphs = sorted_data[i + 1]
        
        # Only check consecutive pages
        if next_page_num != curr_page_num + 1:
            continue
        
        # Skip if either page has no paragraphs
        if not curr_paragraphs or not next_paragraphs:
            continue
        
        # Check if last paragraph of current page should merge with first of next page
        last_para = curr_paragraphs[-1]
        first_para = next_paragraphs[0]
        
        should_merge, reason = should_merge_cross_page_paragraphs(
            last_para,
            first_para,
            original_texts,
            debug=debug
        )
        
        if should_merge:
            # Merge: append first_para fragments to last_para
            curr_paragraphs[-1].extend(first_para)
            
            # Remove first_para from next page
            next_paragraphs.pop(0)
            
            merge_count += 1
            
            if debug:
                print(f"  Merged paragraph across pages {curr_page_num}->{next_page_num}: {reason}")
    
    if merge_count > 0:
        print(f"  Cross-page merge: Combined {merge_count} paragraph(s) spanning page boundaries")
    
    return sorted_data


def create_unified_xml(
    pdf_path: str,
    merged_data: Dict[int, Dict[str, Any]],
    pdftohtml_xml_path: str,
    output_xml_path: str,
) -> None:
    """
    Generate the final unified XML with hierarchical structure.

    XML structure:
    <document>
      <page>
        <texts>
          <para col_id="..." reading_block="...">
            <text reading_order="..." ...>...</text>
            <text reading_order="..." ...>...</text>
          </para>
        </texts>
        <media>
          <media reading_order="..." reading_block="..." .../>
        </media>
        <tables>
          <table reading_order="..." reading_block="..." ...>...</table>
        </tables>
      </page>
    </document>
    """
    # Parse original pdftohtml XML to get font/size/color attributes
    original_tree = ET.parse(pdftohtml_xml_path)
    original_root = original_tree.getroot()

    # Build a lookup: (page, stream_index) -> original <text> element
    original_texts = {}
    for page_elem in original_root.findall(".//page"):
        page_num = int(page_elem.get("number", "0"))
        stream_idx = 1
        for text_elem in page_elem.findall("text"):
            original_texts[(page_num, stream_idx)] = text_elem
            stream_idx += 1

    # Create new unified XML
    root = ET.Element("document", {"source": os.path.basename(pdf_path)})

    # Copy <fontspec> elements from original pdftohtml XML to unified XML
    # This is critical for font_roles_auto.py to work correctly
    for fontspec_elem in original_root.findall(".//fontspec"):
        # Clone the fontspec element with all its attributes
        fontspec_copy = ET.SubElement(root, "fontspec", fontspec_elem.attrib)
        print(f"  Added fontspec: id={fontspec_elem.get('id')}, size={fontspec_elem.get('size')}")

    # Copy <outline> element if present (for chapter detection)
    # The outline element contains PDF bookmarks/TOC information
    outline_elem = original_root.find(".//outline")
    if outline_elem is not None:
        print("  Found <outline> element - copying to unified XML for chapter detection")

        def copy_outline_recursive(source_elem, parent_elem):
            """Recursively copy outline structure including nested outlines."""
            for child in source_elem:
                if child.tag == "item":
                    # Copy item with its attributes and text
                    item_copy = ET.SubElement(parent_elem, "item", child.attrib)
                    item_copy.text = child.text
                    item_copy.tail = child.tail
                elif child.tag == "outline":
                    # Recursively copy nested outline
                    nested_outline = ET.SubElement(parent_elem, "outline", child.attrib)
                    copy_outline_recursive(child, nested_outline)

        # Create outline element in unified XML
        outline_copy = ET.SubElement(root, "outline")
        copy_outline_recursive(outline_elem, outline_copy)
        print(f"  Copied outline with {len(list(outline_elem.iter('item')))} items")

    # PHASE 1: Collect all paragraphs from all pages (before XML generation)
    # This allows us to merge cross-page paragraphs in a second pass
    print("\nPhase 1: Creating paragraphs for all pages...")
    all_page_data = []  # List of (page_num, page_data, page_number_id, sorted_fragments, paragraphs)
    
    for page_num in sorted(merged_data.keys()):
        page_data = merged_data[page_num]

        # Extract page number ID from dedicated page_number_fragments (not filtered fragments)
        page_number_id = extract_page_number(
            page_data.get("page_number_fragments", []),
            page_data["page_height"]
        )

        # Sort fragments using Excel metadata: ReadingOrderBlock → ColID → Baseline
        sorted_fragments = sorted(
            page_data["fragments"],
            key=lambda x: (x["reading_order_block"], x["col_id"], x["baseline"])
        )

        # Calculate typical line height for paragraph break detection
        if sorted_fragments:
            line_heights = [f["height"] for f in sorted_fragments if f["height"] > 0]
            typical_line_height = sorted(line_heights)[len(line_heights) // 2] if line_heights else 12.0
        else:
            typical_line_height = 12.0

        # Group fragments by reading order block
        print(f"  Page {page_num}: Grouping {len(sorted_fragments)} fragments into paragraphs by reading order block")

        page_paragraphs = []  # All paragraphs for this page
        
        for reading_block, block_fragments_iter in groupby(sorted_fragments, key=lambda x: x["reading_order_block"]):
            block_fragments = list(block_fragments_iter)

            print(f"    Reading Block {reading_block}: Processing {len(block_fragments)} fragments")

            # Within this reading order block, group fragments into paragraphs using font-aware logic
            paragraphs = group_fragments_into_paragraphs(
                block_fragments,
                typical_line_height,
                page_num=page_num,
                debug=False,
                page_width=page_data["page_width"],
                original_texts=original_texts  # Pass font info for smart grouping
            )

            print(f"    Reading Block {reading_block}: Created {len(paragraphs)} paragraphs")
            
            # Collect paragraphs for this page
            page_paragraphs.extend(paragraphs)
        
        # Store all data for this page
        all_page_data.append((page_num, page_data, page_number_id, page_paragraphs))
    
    # PHASE 2: Merge cross-page paragraphs
    print("\nPhase 2: Merging paragraphs across page boundaries...")
    paragraph_data_for_merge = [(page_num, paragraphs) for page_num, _, _, paragraphs in all_page_data]
    merged_paragraph_data = merge_cross_page_paragraphs(
        paragraph_data_for_merge,
        original_texts,
        debug=False
    )
    
    # Update all_page_data with merged paragraphs
    merged_dict = {page_num: paragraphs for page_num, paragraphs in merged_paragraph_data}
    all_page_data = [(page_num, page_data, page_number_id, merged_dict.get(page_num, paragraphs)) 
                     for page_num, page_data, page_number_id, paragraphs in all_page_data]
    
    # PHASE 3: Generate XML from merged paragraphs
    print("\nPhase 3: Generating unified XML...")
    for page_num, page_data, page_number_id, page_paragraphs in all_page_data:
        # Build page attributes
        page_attrs = {
            "number": str(page_num),
            "width": str(page_data["page_width"]),
            "height": str(page_data["page_height"]),
        }

        # Add page ID if found
        if page_number_id:
            page_attrs["id"] = f"page_{page_number_id}"

        page_elem = ET.SubElement(root, "page", page_attrs)

        # Texts section with paragraph grouping
        texts_elem = ET.SubElement(page_elem, "texts")

        # Generate XML for each paragraph on this page
        for para_fragments in page_paragraphs:
            if not para_fragments:
                continue

            # Create <para> element with col_id and reading_block from first fragment
            first_fragment = para_fragments[0]
            para_attrs = {
                "col_id": str(first_fragment["col_id"]),
                "reading_block": str(first_fragment["reading_order_block"]),
            }
            para_elem = ET.SubElement(texts_elem, "para", para_attrs)

            # Add all text elements in this paragraph
            for f in para_fragments:
                # Get original attributes from pdftohtml XML
                orig_elem = original_texts.get((page_num, f["stream_index"]))

                text_attrs = {
                    "reading_order": str(f["reading_order_index"]),
                    "row_index": str(f["row_index"]),
                    "baseline": str(f["baseline"]),
                    "left": str(f["left"]),
                    "top": str(f["top"]),
                    "width": str(f["width"]),
                    "height": str(f["height"]),
                }

                # Add original attributes if available (font, size, etc.)
                if orig_elem is not None:
                    for attr_name in orig_elem.attrib:
                        if attr_name not in text_attrs:
                            text_attrs[attr_name] = orig_elem.get(attr_name)

                text_elem = ET.SubElement(para_elem, "text", text_attrs)

                # NEW: Check if we have original fragments (RittDocDTD-compliant output)
                if "original_fragments" in f and len(f["original_fragments"]) > 1:
                    # Use inline elements to preserve font information
                    for orig_frag in f["original_fragments"]:
                        # Get font info from pdftohtml XML
                        orig_stream_idx = orig_frag.get("stream_index")
                        orig_pdftohtml = original_texts.get((page_num, orig_stream_idx))
                        
                        # Determine element type based on fragment properties
                        if orig_frag.get("is_script"):
                            if orig_frag["script_type"] == "subscript":
                                elem_name = "subscript"
                            else:
                                elem_name = "superscript"
                        else:
                            elem_name = "phrase"
                        
                        # Create inline element
                        inline_attrs = {}
                        if orig_pdftohtml is not None:
                            for attr in ["font", "size", "color"]:
                                if attr in orig_pdftohtml.attrib:
                                    inline_attrs[attr] = orig_pdftohtml.get(attr)
                        
                        inline_elem = ET.SubElement(text_elem, elem_name, inline_attrs)
                        inline_elem.text = orig_frag.get("text", "")
                else:
                    # Fallback: Use old approach for single fragments or no tracking
                    # Preserve inner XML formatting (e.g., <i>, <b>, <emphasis>)
                    inner_xml = f.get("inner_xml", f["text"])
                    if inner_xml and inner_xml != f["text"]:
                        # Parse the inner XML and attach to text_elem
                        try:
                            # Wrap in temporary root to parse fragments
                            wrapped = f"<root>{inner_xml}</root>"
                            temp_root = ET.fromstring(wrapped)
                            # Copy text and all child elements
                            text_elem.text = temp_root.text
                            for child in temp_root:
                                text_elem.append(child)
                            # Preserve tail text after last element
                            if len(temp_root) > 0 and temp_root[-1].tail:
                                text_elem[-1].tail = temp_root[-1].tail
                        except ET.ParseError:
                            # Fallback to plain text if XML parsing fails
                            text_elem.text = f["text"]
                    else:
                        # No formatting, use plain text
                        text_elem.text = f["text"]

        # Get page dimensions for coordinate transformation
        html_page_width = page_data.get("page_width", 0)
        html_page_height = page_data.get("page_height", 0)
        media_page_width = page_data.get("media_page_width", 0)
        media_page_height = page_data.get("media_page_height", 0)
        
        # Media section - all images positioned by bbox reading order
        # CRITICAL: Transform coordinates from PyMuPDF space to HTML space
        media_elem = ET.SubElement(page_elem, "media")
        # Sort by reading_block, then reading_order
        for elem, reading_order, reading_block in sorted(page_data["media"], key=lambda x: (x[2], x[1])):
            # Clone the element
            new_elem = ET.SubElement(media_elem, elem.tag, elem.attrib)
            new_elem.set("reading_order", str(reading_order))
            new_elem.set("reading_block", str(reading_block))
            
            # Transform coordinates to HTML space to match text coordinates
            if media_page_width > 0 and media_page_height > 0:
                transform_media_coords_to_html(
                    new_elem, 
                    media_page_width, 
                    media_page_height,
                    html_page_width,
                    html_page_height
                )
            
            # Copy all child elements
            for child in elem:
                new_elem.append(child)

        # Tables section
        # CRITICAL: Transform coordinates from PyMuPDF space to HTML space
        tables_elem = ET.SubElement(page_elem, "tables")
        # Sort by reading_block, then reading_order
        for elem, reading_order, reading_block in sorted(page_data["tables"], key=lambda x: (x[2], x[1])):
            # Clone the element
            new_elem = ET.SubElement(tables_elem, elem.tag, elem.attrib)
            new_elem.set("reading_order", str(reading_order))
            new_elem.set("reading_block", str(reading_block))
            
            # Transform coordinates to HTML space to match text coordinates
            if media_page_width > 0 and media_page_height > 0:
                transform_media_coords_to_html(
                    new_elem,
                    media_page_width,
                    media_page_height,
                    html_page_width,
                    html_page_height
                )
            
            # Copy all child elements
            for child in elem:
                new_elem.append(child)

    # Write XML
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_xml_path, encoding="utf-8", xml_declaration=True)

    # Count tables and media written
    total_tables_written = len(root.findall('.//tables/table'))
    total_media_written = len(root.findall('.//media/media'))
    total_pages = len(root.findall('.//page'))
    pages_with_tables = len([p for p in root.findall('.//page') if len(p.findall('.//tables/table')) > 0])
    pages_with_media = len([p for p in root.findall('.//page') if len(p.findall('.//media/media')) > 0])
    
    print(f"Unified XML saved to: {output_xml_path}")
    print(f"  Pages: {total_pages}")
    print(f"  Tables: {total_tables_written} (across {pages_with_tables} pages)")
    print(f"  Media: {total_media_written} (across {pages_with_media} pages)")
    print(f"  ✓ All coordinates normalized to HTML space (matching text elements)")


def run_font_roles_auto(unified_xml_path: str) -> str:
    """
    Run font_roles_auto.py to derive font roles from unified XML.

    Args:
        unified_xml_path: Path to unified XML

    Returns:
        Path to font roles JSON file
    """
    base_name = Path(unified_xml_path).stem.replace("_unified", "")
    base_dir = Path(unified_xml_path).parent
    font_roles_path = base_dir / f"{base_name}_font_roles.json"

    print("  Running font_roles_auto.py...")
    cmd = [
        sys.executable,
        "font_roles_auto.py",
        str(unified_xml_path),
        "--out", str(font_roles_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ⚠ Warning: font_roles_auto.py failed:")
        print(result.stderr)
        return ""

    print(f"  ✓ Font roles: {font_roles_path}")
    return str(font_roles_path)


def run_heuristics(unified_xml_path: str, font_roles_path: str) -> str:
    """
    Run heuristics_Nov3.py to create structured DocBook XML.

    Args:
        unified_xml_path: Path to unified XML
        font_roles_path: Path to font roles JSON

    Returns:
        Path to structured DocBook XML file
    """
    base_name = Path(unified_xml_path).stem.replace("_unified", "")
    base_dir = Path(unified_xml_path).parent
    structured_xml_path = base_dir / f"{base_name}_structured.xml"

    print("  Running heuristics_Nov3.py...")
    cmd = [
        sys.executable,
        "heuristics_Nov3.py",
        str(unified_xml_path),
        "--font-roles", str(font_roles_path),
        "--out", str(structured_xml_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ⚠ Warning: heuristics_Nov3.py failed:")
        print(result.stderr)
        return ""

    print(f"  ✓ Structured XML: {structured_xml_path}")
    return str(structured_xml_path)


def run_docbook_packaging(structured_xml_path: str, metadata_dir: Optional[str] = None) -> str:
    """
    Run create_book_package.py to package DocBook XML into ZIP.

    Args:
        structured_xml_path: Path to structured DocBook XML
        metadata_dir: Optional directory containing metadata.csv or metadata.xls/xlsx

    Returns:
        Path to output ZIP file
    """
    base_name = Path(structured_xml_path).stem.replace("_structured", "")
    base_dir = Path(structured_xml_path).parent
    output_dir = base_dir / f"{base_name}_package"

    print("  Running create_book_package.py...")
    cmd = [
        sys.executable,
        "create_book_package.py",
        "--input", str(structured_xml_path),
        "--out", str(output_dir)
    ]
    
    # Add metadata directory if provided
    if metadata_dir:
        cmd.extend(["--metadata-dir", str(metadata_dir)])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ⚠ Warning: create_book_package.py failed:")
        print(result.stderr)
        return ""

    # Find the generated ZIP file
    zip_files = list(output_dir.glob("*.zip"))
    if zip_files:
        print(f"  ✓ Package: {zip_files[0]}")
        return str(zip_files[0])

    return ""


def process_pdf_to_unified_xml(
    pdf_path: str,
    output_dir: str = None,
    dpi: int = 200,
    require_table_caption: bool = True,
    max_caption_distance: float = 100.0,
) -> str:
    """
    Main orchestration function.

    Args:
        pdf_path: Path to input PDF
        output_dir: Optional output directory (default: same as PDF)
        dpi: DPI for image rendering
        require_table_caption: If True, filter out tables without "Table X" captions
        max_caption_distance: Maximum distance between table and caption in points

    Returns:
        Path to unified XML file
    """
    pdf_path = os.path.abspath(pdf_path)
    base_dir = os.path.dirname(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    print(f"\n{'='*60}")
    print(f"Processing: {os.path.basename(pdf_path)}")
    print(f"{'='*60}\n")
    
    # CRITICAL: Reset reference mapper for this conversion
    # This ensures clean state and enables image tracking throughout the pipeline
    if HAS_REFERENCE_MAPPER:
        reset_mapper()
        print("✓ Reference mapper initialized for image tracking\n")

    # Step 1: Process text with reading order
    print("Step 1: Processing text and reading order...")
    text_data = pdf_to_excel_with_columns(pdf_path)
    print(f"  ✓ Excel output: {text_data['excel_path']}")
    print(f"  ✓ Processed {len(text_data['pages'])} pages\n")
    gc.collect()  # Free memory after text processing

    # Step 2: Extract media
    print("Step 2: Extracting media (images, tables, vectors)...")
    media_xml_path = extract_media_and_tables(
        pdf_path,
        dpi=dpi,
        require_table_caption=require_table_caption,
        max_caption_distance=max_caption_distance,
    )
    print(f"  ✓ Media XML: {media_xml_path}\n")
    gc.collect()  # Free memory after media extraction

    # Step 3: Parse media XML
    print("Step 3: Parsing media data...")
    media_data = parse_media_xml(media_xml_path)
    
    # Count total tables found
    total_tables_in_media = sum(len(page_data.get("tables", [])) for page_data in media_data.values())
    pages_with_tables = sum(1 for page_data in media_data.values() if len(page_data.get("tables", [])) > 0)
    
    print(f"  ✓ Found media on {len(media_data)} pages")
    print(f"  ✓ Found {total_tables_in_media} tables across {pages_with_tables} pages\n")
    gc.collect()  # Free memory after parsing

    # Step 4: Merge text and media (simple bbox-based positioning)
    print("Step 4: Merging text and media...")
    merged_data = merge_text_and_media_simple(text_data, media_data)
    print(f"  ✓ Merged data for {len(merged_data)} pages\n")
    gc.collect()  # Free memory after merging

    # Step 5: Generate unified XML with page number IDs
    print("Step 5: Generating unified XML with page number IDs...")
    output_xml_path = os.path.join(base_dir, f"{base_name}_unified.xml")
    create_unified_xml(
        pdf_path,
        merged_data,
        text_data["pdftohtml_xml_path"],
        output_xml_path,
    )
    print(f"  ✓ Done!\n")

    # Export reference mapping for debugging
    if HAS_REFERENCE_MAPPER:
        try:
            mapper = get_mapper()
            mapping_path = os.path.join(base_dir, f"{base_name}_reference_mapping_phase1.json")
            mapper.export_to_json(Path(mapping_path))
            print(f"\n  ✓ Reference mapping exported: {mapping_path}")
            
            # Print summary
            report = mapper.generate_report()
            print(f"\n{report}")
        except Exception as e:
            print(f"\n  ⚠ Warning: Could not export reference mapping: {e}")

    print(f"{'='*60}")
    print("PHASE 1 COMPLETE: Unified XML with Page Numbers")
    print(f"{'='*60}")
    print(f"  - Excel (debug): {text_data['excel_path']}")
    print(f"  - Media XML: {media_xml_path}")
    print(f"  - Unified XML: {output_xml_path}")
    print(f"  - Media folder: {base_name}_MultiMedia/")
    print(f"{'='*60}\n")

    return output_xml_path


def process_pdf_to_docbook_package(
    pdf_path: str,
    output_dir: str = None,
    dpi: int = 200,
    skip_packaging: bool = False,
    metadata_dir: str = None,
    dtd_path: str = "RITTDOCdtd/v1.1/RittDocBook.dtd",
    skip_validation: bool = False,
    require_table_caption: bool = True,
    max_caption_distance: float = 100.0,
) -> Dict[str, str]:
    """
    Complete PDF to DocBook pipeline - master integration function.

    This function orchestrates the entire pipeline:
    1. Create unified XML with page numbers
    2. Auto-derive font roles
    3. Apply heuristics for DocBook structure
    4. Package into deliverable ZIP
    5. Run RittDoc validation and create compliant package

    Args:
        pdf_path: Path to input PDF
        output_dir: Optional output directory (default: same as PDF)
        dpi: DPI for image rendering
        skip_packaging: If True, skip the final packaging step
        metadata_dir: Optional directory containing metadata.csv or metadata.xls/xlsx
                     (defaults to PDF directory)
        dtd_path: Path to DTD file for validation
        skip_validation: If True, skip the validation step
        require_table_caption: If True, filter out tables without "Table X" captions
        max_caption_distance: Maximum distance between table and caption in points

    Returns:
        Dictionary with paths to all outputs
    """
    # Phase 1: Create unified XML
    unified_xml_path = process_pdf_to_unified_xml(
        pdf_path,
        output_dir,
        dpi,
        require_table_caption=require_table_caption,
        max_caption_distance=max_caption_distance,
    )
    
    # Default metadata directory to PDF's directory
    if metadata_dir is None:
        metadata_dir = str(Path(pdf_path).parent)

    outputs = {
        "unified_xml": unified_xml_path,
        "font_roles": "",
        "structured_xml": "",
        "package_zip": "",
        "validated_zip": "",
        "validation_report": "",
    }

    # Phase 2: DocBook processing (optional - only if heuristics files exist)
    if not os.path.exists("font_roles_auto.py"):
        print("\n⚠ Skipping DocBook processing: font_roles_auto.py not found")
        print("Phase 1 complete - unified XML with page numbers created.\n")
        return outputs

    print(f"\n{'='*60}")
    print("PHASE 2: DocBook Processing")
    print(f"{'='*60}\n")

    # Step 6: Auto-derive font roles
    print("Step 6: Auto-deriving font roles...")
    font_roles_path = run_font_roles_auto(unified_xml_path)
    outputs["font_roles"] = font_roles_path
    gc.collect()  # Free memory after font roles

    if not font_roles_path:
        print("\n⚠ Stopping: Font roles derivation failed")
        return outputs

    # Step 7: Apply heuristics
    print("\nStep 7: Applying heuristics to create structured DocBook XML...")
    structured_xml_path = run_heuristics(unified_xml_path, font_roles_path)
    outputs["structured_xml"] = structured_xml_path
    gc.collect()  # Free memory after heuristics

    if not structured_xml_path:
        print("\n⚠ Stopping: Heuristics processing failed")
        return outputs

    # Step 8: Package DocBook (optional)
    if not skip_packaging and os.path.exists("create_book_package.py"):
        print("\nStep 8: Packaging DocBook XML...")
        package_zip_path = run_docbook_packaging(structured_xml_path, metadata_dir)
        outputs["package_zip"] = package_zip_path

    # Step 9: RittDoc Validation (optional)
    if outputs["package_zip"] and not skip_validation and VALIDATION_AVAILABLE:
        print(f"\n{'='*60}")
        print("PHASE 3: RittDoc Validation & Compliance")
        print(f"{'='*60}\n")

        print("Step 9: Running RittDoc validation and compliance fixes...")

        # Check if DTD exists
        dtd_file = Path(dtd_path)
        if not dtd_file.exists():
            print(f"  ⚠ Warning: DTD file not found at {dtd_path}")
            print("  Skipping validation step.")
        else:
            try:
                # Determine output paths
                package_path = Path(outputs["package_zip"])
                base_name = package_path.stem.replace("pre_fixes_", "").replace("_structured", "")
                validated_zip_path = package_path.parent / f"{base_name}_rittdoc.zip"
                validation_report_path = package_path.parent / f"{base_name}_validation_report.xlsx"

                # Run the compliance pipeline
                pipeline = RittDocCompliancePipeline(dtd_file)
                success = pipeline.run(
                    input_zip=package_path,
                    output_zip=validated_zip_path,
                    max_iterations=3
                )

                outputs["validated_zip"] = str(validated_zip_path)

                # Check for validation report
                if validation_report_path.exists():
                    outputs["validation_report"] = str(validation_report_path)

                if success:
                    print(f"\n  ✓ Validation passed! Compliant package: {validated_zip_path}")
                else:
                    print(f"\n  ⚠ Validation completed with some errors remaining.")
                    print(f"    Review: {validation_report_path}")

            except Exception as e:
                print(f"  ✗ Validation failed: {e}")
                import traceback
                traceback.print_exc()
    elif outputs["package_zip"] and not skip_validation and not VALIDATION_AVAILABLE:
        print("\n⚠ Skipping validation: rittdoc_compliance_pipeline not available")
    elif skip_validation:
        print("\n⚠ Skipping validation: --skip-validation flag set")

    print(f"\n{'='*60}")
    print("✓ COMPLETE: Full PDF to DocBook Pipeline")
    print(f"{'='*60}")
    print("Final Outputs:")
    print(f"  - Unified XML: {outputs['unified_xml']}")
    if outputs["font_roles"]:
        print(f"  - Font Roles: {outputs['font_roles']}")
    if outputs["structured_xml"]:
        print(f"  - Structured XML: {outputs['structured_xml']}")
    if outputs["package_zip"]:
        print(f"  - Package ZIP (pre-validation): {outputs['package_zip']}")
    if outputs["validated_zip"]:
        print(f"  - Validated ZIP (RittDoc compliant): {outputs['validated_zip']}")
    if outputs["validation_report"]:
        print(f"  - Validation Report: {outputs['validation_report']}")
    print(f"{'='*60}\n")

    return outputs


def main():
    parser = argparse.ArgumentParser(
        description="""
        Master PDF to DocBook Integration Script

        This script orchestrates the complete PDF → DocBook pipeline:
        1. Extract text with reading order and column detection
        2. Extract media (images, tables, vectors)
        3. Merge and create unified XML with page number IDs
        4. Auto-derive font roles (with --full-pipeline)
        5. Apply heuristics for DocBook structure (with --full-pipeline)
        6. Package into deliverable ZIP (with --full-pipeline)
        7. Run RittDoc validation and create compliant package (with --full-pipeline)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("pdf_path", help="Path to input PDF file")
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="DPI for image rendering (default: 200)",
    )
    parser.add_argument(
        "--out",
        dest="output_dir",
        help="Optional output directory (default: same as PDF)",
    )
    parser.add_argument(
        "--full-pipeline",
        action="store_true",
        help="Run full DocBook processing pipeline (font roles, heuristics, packaging)",
    )
    parser.add_argument(
        "--skip-packaging",
        action="store_true",
        help="Skip final ZIP packaging step (only applies with --full-pipeline)",
    )
    parser.add_argument(
        "--metadata-dir",
        help="Directory containing metadata.csv or metadata.xls/xlsx (default: PDF directory)",
    )
    parser.add_argument(
        "--dtd",
        default="RITTDOCdtd/v1.1/RittDocBook.dtd",
        help="Path to DTD file for validation (default: RITTDOCdtd/v1.1/RittDocBook.dtd)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip RittDoc validation step (only applies with --full-pipeline)",
    )
    parser.add_argument(
        "--no-caption-filter",
        action="store_true",
        help="Include all detected tables, even without 'Table X' captions. "
             "May include false positives but ensures no tables are missed.",
    )
    parser.add_argument(
        "--caption-distance",
        type=float,
        default=100.0,
        help="Maximum distance (in points) between table and caption for matching. "
             "Default: 100.0. Increase to capture tables with distant captions.",
    )

    args = parser.parse_args()

    # Run appropriate pipeline based on flags
    if args.full_pipeline:
        # Run complete pipeline
        outputs = process_pdf_to_docbook_package(
            pdf_path=args.pdf_path,
            output_dir=args.output_dir,
            dpi=args.dpi,
            skip_packaging=args.skip_packaging,
            metadata_dir=args.metadata_dir,
            dtd_path=args.dtd,
            skip_validation=args.skip_validation,
            require_table_caption=not args.no_caption_filter,
            max_caption_distance=args.caption_distance,
        )
    else:
        # Just create unified XML with page numbers
        unified_xml_path = process_pdf_to_unified_xml(
            pdf_path=args.pdf_path,
            output_dir=args.output_dir,
            dpi=args.dpi,
            require_table_caption=not args.no_caption_filter,
            max_caption_distance=args.caption_distance,
        )


if __name__ == "__main__":
    main()
