import os
import sys
import argparse
import gc
import fitz          # PyMuPDF
import camelot       # Camelot-py for table detection
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple, Optional

# Import reference mapper for tracking resource transformations
try:
    from reference_mapper import get_mapper
    HAS_REFERENCE_MAPPER = True
except ImportError:
    HAS_REFERENCE_MAPPER = False
    print("Warning: reference_mapper not available, resource tracking disabled")


# ----------------------------
# Utility helpers
# ----------------------------

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def sanitize_xml_text(text: str) -> str:
    """
    Sanitize text for XML by removing invalid characters.

    XML 1.0 allows only:
    - Tab (0x09)
    - Newline (0x0A)
    - Carriage Return (0x0D)
    - Characters >= 0x20

    This removes other control characters that cause XML parsing errors.
    """
    if not text:
        return ""

    # Filter out invalid XML characters
    valid_chars = []
    for char in text:
        code = ord(char)
        # Allow tab, newline, carriage return, and characters >= 0x20
        if code == 0x09 or code == 0x0A or code == 0x0D or code >= 0x20:
            valid_chars.append(char)

    return ''.join(valid_chars)


def rect_iou(r1: fitz.Rect, r2: fitz.Rect) -> float:
    """Intersection-over-union of two PyMuPDF rects."""
    x0 = max(r1.x0, r2.x0)
    y0 = max(r1.y0, r2.y0)
    x1 = min(r1.x1, r2.x1)
    y1 = min(r1.y1, r2.y1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    inter = (x1 - x0) * (y1 - y0)
    area1 = r1.width * r1.height
    area2 = r2.width * r2.height
    denom = area1 + area2 - inter
    return inter / denom if denom > 0 else 0.0


def get_content_area_rect(
    page_rect: fitz.Rect,
    header_margin_pct: float = 0.08,
    footer_margin_pct: float = 0.08,
    left_margin_pct: float = 0.05,
    right_margin_pct: float = 0.05,
) -> fitz.Rect:
    """
    Calculate the content area of a page, excluding headers, footers, and margins.

    Args:
        page_rect: The full page rectangle
        header_margin_pct: Percentage of page height to exclude from top (default: 8%)
        footer_margin_pct: Percentage of page height to exclude from bottom (default: 8%)
        left_margin_pct: Percentage of page width to exclude from left (default: 5%)
        right_margin_pct: Percentage of page width to exclude from right (default: 5%)

    Returns:
        fitz.Rect representing the content area
    """
    page_width = page_rect.width
    page_height = page_rect.height

    content_x0 = page_rect.x0 + (page_width * left_margin_pct)
    content_y0 = page_rect.y0 + (page_height * header_margin_pct)
    content_x1 = page_rect.x1 - (page_width * right_margin_pct)
    content_y1 = page_rect.y1 - (page_height * footer_margin_pct)

    return fitz.Rect(content_x0, content_y0, content_x1, content_y1)


def is_in_content_area(
    rect: fitz.Rect,
    content_area: fitz.Rect,
    min_overlap_pct: float = 0.5,
) -> bool:
    """
    Check if a rectangle is primarily within the content area.

    An element is considered "in content area" if at least min_overlap_pct
    of its area is within the content area bounds.

    Args:
        rect: The rectangle to check (image, vector, table bounds)
        content_area: The content area rectangle
        min_overlap_pct: Minimum percentage of rect that must be in content area (default: 50%)

    Returns:
        True if the rect is primarily within the content area
    """
    if not rect.intersects(content_area):
        return False

    # Calculate intersection
    x0 = max(rect.x0, content_area.x0)
    y0 = max(rect.y0, content_area.y0)
    x1 = min(rect.x1, content_area.x1)
    y1 = min(rect.y1, content_area.y1)

    if x1 <= x0 or y1 <= y0:
        return False

    intersection_area = (x1 - x0) * (y1 - y0)
    rect_area = rect.width * rect.height

    if rect_area <= 0:
        return False

    overlap_pct = intersection_area / rect_area
    return overlap_pct >= min_overlap_pct


def get_text_blocks(page: fitz.Page) -> List[Dict[str, Any]]:
    """
    Get page text as blocks from PyMuPDF.
    Each block: {"bbox": Rect, "text": str}
    """
    blocks = []
    for b in page.get_text("blocks"):
        x0, y0, x1, y1, text, *_ = b
        rect = fitz.Rect(x0, y0, x1, y1)
        blocks.append({"bbox": rect, "text": text.strip()})
    return blocks


def get_page_spans(page: fitz.Page) -> List[Dict[str, Any]]:
    """
    Get detailed text spans for a page, including bbox, font, size, color.
    Each span: {"text": str, "bbox": (x0, y0, x1, y1), "font": str, "size": float, "color": str_hex}
    """
    spans: List[Dict[str, Any]] = []
    text_dict = page.get_text("dict")
    for b in text_dict.get("blocks", []):
        for l in b.get("lines", []):
            for s in l.get("spans", []):
                text = s.get("text", "")
                if not text.strip():
                    continue
                x0, y0, x1, y1 = s.get("bbox", (0, 0, 0, 0))
                rect = (x0, y0, x1, y1)
                font = s.get("font", "")
                size = float(s.get("size", 0.0))
                color_int = s.get("color", 0)
                # color_int is usually 0xRRGGBB
                color_hex = f"#{color_int:06x}"
                spans.append(
                    {
                        "text": text,
                        "bbox": rect,
                        "font": font,
                        "size": size,
                        "color": color_hex,
                    }
                )
    return spans


def spans_in_rect(rect: fitz.Rect, spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return all text spans whose bbox intersects the given rect."""
    inside: List[Dict[str, Any]] = []
    for s in spans:
        x0, y0, x1, y1 = s["bbox"]
        s_rect = fitz.Rect(x0, y0, x1, y1)
        if s_rect.intersects(rect):
            inside.append(s)
    return inside


def is_text_heavy_region(
    rect: fitz.Rect,
    spans: List[Dict[str, Any]],
    char_threshold: int = 150,
    coverage_threshold: float = 0.5,
) -> bool:
    """
    Heuristic to decide if a region is mostly 'text panel' rather than diagram.
    """
    region_area = rect.width * rect.height
    if region_area <= 0:
        return False

    spans_here = spans_in_rect(rect, spans)
    if not spans_here:
        return False

    total_chars = 0
    span_area_sum = 0.0

    for s in spans_here:
        text = s["text"]
        total_chars += len(text)
        x0, y0, x1, y1 = s["bbox"]
        span_area_sum += max(0.0, (x1 - x0)) * max(0.0, (y1 - y0))

    coverage = span_area_sum / region_area

    if total_chars > char_threshold:
        return True
    if coverage > coverage_threshold:
        return True
    return False


def has_complex_drawing_shapes(
    rect: fitz.Rect,
    drawings: List[Dict[str, Any]],
    min_curves: int = 1,
    min_complex_lines: int = 3,
) -> bool:
    """
    Detect if a region contains complex drawing shapes that indicate it's a diagram
    rather than just simple text boxes or underlines.

    Complex shapes include:
    - Curves (bezier curves for circles, ovals, arcs)
    - Multiple non-rectangular lines (arrows, complex shapes)
    - Quads that form non-rectangular shapes

    Args:
        rect: The bounding box region to check
        drawings: List of drawing dictionaries from page.get_drawings()
        min_curves: Minimum number of curves to consider it complex (default: 1)
        min_complex_lines: Minimum number of lines that suggest complex shapes (default: 3)

    Returns:
        True if the region contains complex drawing shapes
    """
    if not drawings:
        return False

    # Count different types of drawing primitives in this region
    curve_count = 0
    line_count = 0
    quad_count = 0
    rect_count = 0

    for drawing in drawings:
        # Check if this drawing intersects with our region
        draw_rect = fitz.Rect(drawing.get("rect", (0, 0, 0, 0)))
        if not draw_rect.intersects(rect):
            continue

        # Analyze the drawing items
        items = drawing.get("items", [])

        for item in items:
            # Each item is a tuple: (operator, *points)
            # operator can be: 'l' (line), 'c' (curve), 're' (rectangle), 'qu' (quad)
            if not item:
                continue

            operator = item[0]

            if operator == "c":  # Bezier curve - often used for circles, ovals, arcs
                curve_count += 1
            elif operator == "l":  # Line
                line_count += 1
            elif operator == "qu":  # Quad
                quad_count += 1
            elif operator == "re":  # Rectangle
                rect_count += 1

    # Decision logic:
    # 1. If we have any curves, it's likely a diagram (circles, ovals, arcs)
    if curve_count >= min_curves:
        return True

    # 2. If we have multiple lines but few/no rectangles, it's likely a complex shape
    #    (arrows, diagrams with connectors, etc.)
    if line_count >= min_complex_lines and rect_count <= 2:
        return True

    # 3. If we have multiple quads (which aren't simple rectangles when used in drawings)
    if quad_count >= 2:
        return True

    # 4. Complex combination: some curves + some lines (labeled diagrams)
    if curve_count > 0 and line_count >= 2:
        return True

    return False


def is_table_like_drawing_region(
    rect: fitz.Rect,
    drawings: List[Dict[str, Any]],
    min_parallel_lines: int = 4,
    grid_tolerance: float = 5.0,
) -> bool:
    """
    Detect if a region contains table-like drawing patterns.

    Tables are characterized by:
    - Multiple parallel horizontal lines (row separators)
    - Multiple parallel vertical lines (column separators)
    - Lines arranged in a grid pattern
    - Few or no curves (unlike diagrams)

    Args:
        rect: The bounding box region to check
        drawings: List of drawing dictionaries from page.get_drawings()
        min_parallel_lines: Minimum number of parallel lines to consider table-like (default: 4)
        grid_tolerance: Tolerance for grouping parallel lines (default: 5.0 pixels)

    Returns:
        True if the region appears to be a table based on drawing patterns
    """
    if not drawings:
        return False

    # Collect line endpoints within the region
    horizontal_lines = []  # [(y, x0, x1), ...]
    vertical_lines = []    # [(x, y0, y1), ...]
    curve_count = 0

    for drawing in drawings:
        draw_rect = fitz.Rect(drawing.get("rect", (0, 0, 0, 0)))
        if not draw_rect.intersects(rect):
            continue

        items = drawing.get("items", [])
        for item in items:
            if not item or len(item) < 2:
                continue

            operator = item[0]

            if operator == "c":  # Curve - tables don't have curves
                curve_count += 1
            elif operator == "l":  # Line
                # Line format: ('l', Point(x0, y0), Point(x1, y1))
                if len(item) >= 3:
                    try:
                        p0 = item[1]
                        p1 = item[2]
                        x0, y0 = float(p0.x), float(p0.y)
                        x1, y1 = float(p1.x), float(p1.y)

                        # Check if line is within our region
                        if not (rect.x0 <= x0 <= rect.x1 and rect.y0 <= y0 <= rect.y1):
                            continue
                        if not (rect.x0 <= x1 <= rect.x1 and rect.y0 <= y1 <= rect.y1):
                            continue

                        # Determine if horizontal or vertical
                        dx = abs(x1 - x0)
                        dy = abs(y1 - y0)

                        if dy < grid_tolerance and dx > 10:  # Horizontal line
                            y_avg = (y0 + y1) / 2
                            horizontal_lines.append((y_avg, min(x0, x1), max(x0, x1)))
                        elif dx < grid_tolerance and dy > 10:  # Vertical line
                            x_avg = (x0 + x1) / 2
                            vertical_lines.append((x_avg, min(y0, y1), max(y0, y1)))
                    except (AttributeError, TypeError):
                        continue
            elif operator == "re":  # Rectangle - tables often have cell borders
                # Rectangle adds both horizontal and vertical segments
                if len(item) >= 2:
                    try:
                        r = item[1]
                        if hasattr(r, 'x0'):
                            # Add rectangle edges as lines
                            horizontal_lines.append((r.y0, r.x0, r.x1))
                            horizontal_lines.append((r.y1, r.x0, r.x1))
                            vertical_lines.append((r.x0, r.y0, r.y1))
                            vertical_lines.append((r.x1, r.y0, r.y1))
                    except (AttributeError, TypeError):
                        continue

    # If many curves, it's likely a diagram not a table
    if curve_count >= 3:
        return False

    # Group horizontal lines by Y position
    def group_parallel_lines(lines, pos_idx=0, tolerance=grid_tolerance):
        """Group lines that are parallel (same position within tolerance)."""
        if not lines:
            return []
        lines_sorted = sorted(lines, key=lambda l: l[pos_idx])
        groups = []
        current_group = [lines_sorted[0]]
        current_pos = lines_sorted[0][pos_idx]

        for line in lines_sorted[1:]:
            if abs(line[pos_idx] - current_pos) <= tolerance:
                current_group.append(line)
            else:
                groups.append(current_group)
                current_group = [line]
                current_pos = line[pos_idx]
        groups.append(current_group)
        return groups

    h_groups = group_parallel_lines(horizontal_lines, pos_idx=0)
    v_groups = group_parallel_lines(vertical_lines, pos_idx=0)

    # Count distinct parallel line positions (rows/columns)
    h_line_count = len(h_groups)  # Number of distinct horizontal line positions (rows)
    v_line_count = len(v_groups)  # Number of distinct vertical line positions (columns)

    # Table detection: multiple parallel horizontal AND vertical lines
    # Tables typically have 2+ rows and 2+ columns
    if h_line_count >= min_parallel_lines and v_line_count >= 2:
        return True
    if v_line_count >= min_parallel_lines and h_line_count >= 2:
        return True

    # Strong table indicator: many evenly-spaced parallel lines
    if h_line_count >= 3 and v_line_count >= 3:
        return True

    return False


def merge_nearby_rects(
    rects: List[fitz.Rect],
    merge_distance: float = 20.0,
    max_iterations: int = 10,
) -> List[fitz.Rect]:
    """
    Merge rectangles that are close to each other to reduce fragmentation.

    This helps combine fragmented vector drawings that should be one image.
    Rectangles within merge_distance pixels of each other will be combined.
    """
    if not rects:
        return []

    merged = [r for r in rects]  # Copy list

    for _ in range(max_iterations):
        changed = False
        new_merged = []
        used = set()

        for i, r1 in enumerate(merged):
            if i in used:
                continue

            # Try to find rectangles to merge with r1
            current = fitz.Rect(r1)

            for j, r2 in enumerate(merged):
                if j <= i or j in used:
                    continue

                # Check if rectangles are close enough to merge
                # Expand r1 by merge_distance in all directions
                expanded = fitz.Rect(
                    current.x0 - merge_distance,
                    current.y0 - merge_distance,
                    current.x1 + merge_distance,
                    current.y1 + merge_distance,
                )

                if expanded.intersects(r2):
                    # Merge r2 into current
                    current.include_rect(r2)
                    used.add(j)
                    changed = True

            new_merged.append(current)
            used.add(i)

        merged = new_merged

        if not changed:
            break

    return merged


def expand_rect_for_nearby_text(
    rect: fitz.Rect,
    spans: List[Dict[str, Any]],
    max_distance: float = 15.0,
) -> fitz.Rect:
    """
    Expand a rectangle to include nearby text fragments that are part of the drawing.

    This fixes the issue where flowchart labels and diagram text get cropped
    because they're not included in the drawing shape bounds.

    Args:
        rect: The original bounding box from drawing shapes
        spans: List of text spans on the page
        max_distance: Maximum distance (pixels) to search for associated text

    Returns:
        Expanded rectangle that includes nearby text fragments
    """
    if not spans:
        return rect

    expanded = fitz.Rect(rect)  # Copy the original rect

    # Expand search area slightly beyond the drawing bounds
    search_rect = fitz.Rect(
        rect.x0 - max_distance,
        rect.y0 - max_distance,
        rect.x1 + max_distance,
        rect.y1 + max_distance,
    )

    # Find all text spans near or within the drawing boundary
    for span in spans:
        x0, y0, x1, y1 = span["bbox"]
        span_rect = fitz.Rect(x0, y0, x1, y1)

        # Check if span is within search distance
        if not span_rect.intersects(search_rect):
            continue

        # Calculate distance from span to drawing boundary
        # Use center point of span for distance calculation
        span_center_x = (x0 + x1) / 2.0
        span_center_y = (y0 + y1) / 2.0

        # Distance to nearest edge of the drawing rect
        dx = 0.0
        dy = 0.0

        if span_center_x < rect.x0:
            dx = rect.x0 - span_center_x
        elif span_center_x > rect.x1:
            dx = span_center_x - rect.x1

        if span_center_y < rect.y0:
            dy = rect.y0 - span_center_y
        elif span_center_y > rect.y1:
            dy = span_center_y - rect.y1

        distance = (dx * dx + dy * dy) ** 0.5

        # If text is close enough, include it in the expanded bbox
        if distance <= max_distance:
            expanded.include_rect(span_rect)

    return expanded


def is_valid_figure_caption(text: str) -> bool:
    """
    Check if text is a valid figure caption.

    A valid figure caption must:
    - Start with "Figure", "Fig.", "Fig ", "IMAGE", or similar pattern
    - Be followed by a number (e.g., "Figure 1", "Figure 2.3", "Fig. 1-2")
    - Have a delimiter after the number: ".", ":", "-", or space followed by text

    Examples of valid captions:
    - "Figure 1. System Architecture"
    - "Figure 1: Overview"
    - "Figure 1 - Components"
    - "Fig. 2.3: Details"

    Args:
        text: The text to check

    Returns:
        True if text appears to be a valid figure caption
    """
    import re

    if not text or len(text.strip()) < 5:  # "Fig 1" minimum
        return False

    text_stripped = text.strip()
    text_lower = text_stripped.lower()

    # Pattern structure:
    # 1. Keyword (figure, fig, image, etc.)
    # 2. Optional space/dot
    # 3. Number (with optional decimal/letter suffix like 1.2, 1a, 1-2)
    # 4. REQUIRED delimiter: ".", ":", "-", ")", or space followed by more text
    #
    # The delimiter is key - "Figure 1" alone in running text is not a caption,
    # but "Figure 1." or "Figure 1:" is a proper caption label.

    # Number pattern: digits, optionally followed by .digit, -digit, or letter
    num_pattern = r'\d+(?:[\.\-]\d+)?[a-z]?'

    # Delimiter pattern: must have ., :, -, ), or be followed by space+text
    # This ensures "Figure 1." or "Figure 1: description" matches
    # but "see Figure 1 for details" doesn't match (no delimiter after number)
    delim_pattern = r'(?:[\.\:\-\;\)\]]|\s+\w)'

    figure_keywords = [
        r'figure',           # Figure 1.
        r'fig\.',            # Fig. 1.
        r'fig',              # Fig 1.
        r'image',            # Image 1.
        r'img\.',            # Img. 1.
        r'plate',            # Plate 1.
        r'diagram',          # Diagram 1.
        r'illustration',     # Illustration 1.
        r'photo',            # Photo 1.
        r'photograph',       # Photograph 1.
        r'exhibit',          # Exhibit 1.
        r'chart',            # Chart 1.
        r'graph',            # Graph 1.
        r'map',              # Map 1.
        r'drawing',          # Drawing 1.
        r'sketch',           # Sketch 1.
    ]

    for keyword in figure_keywords:
        # Pattern: keyword + optional space + number + delimiter
        pattern = rf'^{keyword}\s*{num_pattern}\s*{delim_pattern}'
        if re.match(pattern, text_lower):
            return True

    return False


def is_valid_table_caption(text: str) -> bool:
    """
    Check if text is a valid table caption.

    A valid table caption must:
    - Start with "Table", "Tbl.", "Tbl ", or similar pattern
    - Be followed by a number (e.g., "Table 1", "Table 2.3", "Tbl. 1-2")
    - Have a delimiter after the number: ".", ":", "-", ";", ")", "]" or space followed by text

    Args:
        text: The text to check

    Returns:
        True if text appears to be a valid table caption
    """
    import re

    if not text or len(text.strip()) < 5:
        return False

    text_stripped = text.strip()
    text_lower = text_stripped.lower()

    # Number pattern: handles 1, 1.2, 1-2, 1a, etc.
    num_pattern = r'\d+(?:[\.\-]\d+)?[a-z]?'

    # Delimiter pattern: requires punctuation or space followed by word character
    # This helps distinguish real captions from false positives
    delim_pattern = r'(?:[\.\:\-\;\)\]]|\s+\w)'

    # Table keywords to look for
    table_keywords = [
        r'table',             # Table 1
        r'tbl\.',             # Tbl. 1
        r'tbl',               # Tbl 1
        r'tableau',           # Tableau 1 (French)
        r'tabelle',           # Tabelle 1 (German)
        r'schedule',          # Schedule 1 (legal docs)
        r'appendix\s+[a-z]?', # Appendix A1, Appendix 1
        r'exhibit',           # Exhibit 1
        r'list',              # List 1
        r'matrix',            # Matrix 1
    ]

    for keyword in table_keywords:
        pattern = rf'^{keyword}\s*{num_pattern}\s*{delim_pattern}'
        if re.match(pattern, text_lower):
            return True

    return False


def find_table_caption(
    region_rect: fitz.Rect,
    blocks: List[Dict[str, Any]],
    max_distance: float = 60.0,
    require_table_pattern: bool = True,
) -> str:
    """
    Find caption for a table region.

    Looks for a "Table X" pattern both ABOVE and BELOW the table,
    preferring the closest match. Tables usually have captions above,
    but some place them below.

    Args:
        region_rect: The bounding box of the table region
        blocks: Text blocks on the page
        max_distance: Maximum distance from table to look for caption
        require_table_pattern: If True, only accept text starting with "Table X" pattern

    Returns:
        Caption string (empty if none found)
    """
    best_caption = ""
    best_distance = None

    for blk in blocks:
        r = blk["bbox"]
        text = blk["text"].strip()

        # Skip empty text
        if not text:
            continue

        # Check horizontal alignment (block must overlap with table horizontally)
        if not (region_rect.x1 > r.x0 and region_rect.x0 < r.x1):
            continue

        # Check if this matches the table pattern (if required)
        if require_table_pattern and not is_valid_table_caption(text):
            continue

        # Calculate distance - check both above and below
        dist = None

        # Check if block is ABOVE the table
        if r.y1 <= region_rect.y0:
            dist = region_rect.y0 - r.y1

        # Check if block is BELOW the table
        elif r.y0 >= region_rect.y1:
            dist = r.y0 - region_rect.y1

        # Skip if not within max distance
        if dist is None or dist > max_distance:
            continue

        # Keep the closest match
        if best_distance is None or dist < best_distance:
            best_distance = dist
            best_caption = text

    return best_caption


def find_figure_caption(
    region_rect: fitz.Rect,
    blocks: List[Dict[str, Any]],
    max_distance: float = 50.0,
    require_figure_pattern: bool = True,
) -> str:
    """
    Find caption for an image/figure region.

    Looks for a "Figure X" pattern both ABOVE and BELOW the image,
    preferring the closest match. Most documents have captions below,
    but some place them above.

    Args:
        region_rect: The bounding box of the image region
        blocks: Text blocks on the page
        max_distance: Maximum distance from image to look for caption
        require_figure_pattern: If True, only accept text starting with "Figure X" pattern

    Returns:
        Caption string (empty if none found)
    """
    best_caption = ""
    best_distance = None

    for blk in blocks:
        r = blk["bbox"]
        text = blk["text"].strip()

        # Skip empty text
        if not text:
            continue

        # Check horizontal alignment (block must overlap with image horizontally)
        if not (region_rect.x1 > r.x0 and region_rect.x0 < r.x1):
            continue

        # Check if this matches the figure pattern (if required)
        if require_figure_pattern and not is_valid_figure_caption(text):
            continue

        # Calculate distance - check both above and below
        dist = None

        # Check if block is ABOVE the image
        if r.y1 <= region_rect.y0:
            dist = region_rect.y0 - r.y1

        # Check if block is BELOW the image
        elif r.y0 >= region_rect.y1:
            dist = r.y0 - region_rect.y1

        # Skip if not within max distance
        if dist is None or dist > max_distance:
            continue

        # Keep the closest match
        if best_distance is None or dist < best_distance:
            best_distance = dist
            best_caption = text

    return best_caption


def find_title_caption_for_region(
    region_rect: fitz.Rect,
    blocks: List[Dict[str, Any]],
    title_max_distance: float = 25.0,
    caption_max_distance: float = 50.0,
    require_figure_pattern: bool = True,
) -> Tuple[str, str]:
    """
    Find caption for an image/figure region.

    This is a compatibility wrapper that returns (title, caption) tuple.
    Since figures typically have only one label (not separate title and caption),
    this returns the caption in the second position and empty string for title.

    Args:
        region_rect: The bounding box of the image region
        blocks: Text blocks on the page
        title_max_distance: Ignored (kept for compatibility)
        caption_max_distance: Maximum distance from image to look for caption
        require_figure_pattern: If True, only accept captions starting with "Figure X" pattern

    Returns:
        Tuple of ("", caption) - title is always empty, caption contains the figure label
    """
    caption = find_figure_caption(
        region_rect,
        blocks,
        max_distance=caption_max_distance,
        require_figure_pattern=require_figure_pattern,
    )

    # Return empty title, caption contains the figure label
    return "", caption


def has_figure_keywords_nearby(
    region_rect: fitz.Rect,
    blocks: List[Dict[str, Any]],
    max_distance: float = 100.0,
    horizontal_tolerance: float = 50.0,
) -> bool:
    """
    Check if there's text containing "Figure", "Image", or "Table" near the region.

    Looks for keywords in text blocks both above and below the region.

    Args:
        region_rect: The bounding box of the image/vector region
        blocks: Text blocks on the page
        max_distance: Maximum distance to search for keywords (default: 100.0)
        horizontal_tolerance: Extra horizontal margin for alignment check (default: 50.0)

    Returns:
        True if any nearby text contains figure-related keywords
    """
    keywords = ["figure", "image", "table", "fig.", "fig ", "tbl.", "tbl "]

    for blk in blocks:
        r = blk["bbox"]
        text_lower = blk["text"].lower()

        # Check if any keyword is in the text
        if not any(keyword in text_lower for keyword in keywords):
            continue

        # Check if block is within the region (caption embedded in diagram)
        if region_rect.contains(r) or region_rect.intersects(r):
            return True

        # Check if block is horizontally aligned (overlaps in x-axis)
        # Use tolerance to be more lenient with alignment
        region_x_min = region_rect.x0 - horizontal_tolerance
        region_x_max = region_rect.x1 + horizontal_tolerance
        if not (region_x_max > r.x0 and region_x_min < r.x1):
            continue

        # Check if block is above the region
        if r.y1 <= region_rect.y0:
            dist = region_rect.y0 - r.y1
            if 0 <= dist <= max_distance:
                return True

        # Check if block is below the region
        if r.y0 >= region_rect.y1:
            dist = r.y0 - region_rect.y1
            if 0 <= dist <= max_distance:
                return True

    return False


def get_links_overlapping_rect(page: fitz.Page, rect: fitz.Rect) -> List[str]:
    """Collect all hyperlink URIs whose annotation rect intersects the given region."""
    links: List[str] = []
    annots = page.annots()
    if not annots:
        return links
    for a in annots:
        try:
            if a.type[0] == fitz.PDF_ANNOT_LINK and a.rect.intersects(rect):
                uri = a.uri or ""
                if uri:
                    links.append(uri)
        except Exception:
            continue
    return links


def camelot_bbox_to_fitz_rect(
    bbox: Tuple[float, float, float, float],
    page_height: float,
) -> fitz.Rect:
    """
    Convert Camelot bbox (x1, y1, x2, y2) with bottom-left origin
    to PyMuPDF Rect with top-left origin.
    """
    x1, y1, x2, y2 = bbox  # Camelot bottom-left
    # Invert Y axis
    y0_fitz = page_height - y2
    y1_fitz = page_height - y1
    return fitz.Rect(x1, y0_fitz, x2, y1_fitz)


# ----------------------------
# Raster image extraction
# ----------------------------

def extract_raster_images_for_page(
    page: fitz.Page,
    page_no: int,
    blocks: List[Dict[str, Any]],
    media_dir: str,
    page_el: ET.Element,
    content_area: Optional[fitz.Rect] = None,
    dpi: int = 200,
    min_size: float = 5.0,
    full_page_threshold: float = 0.85,
    max_caption_chars: int = 200,
    icon_size_threshold: float = 100.0,  # Images smaller than this are treated as inline icons
) -> List[fitz.Rect]:
    """
    Extract raster images on a single page.

    Rules:
      - Ignore images in header/footer/margin areas (outside content_area).
      - Ignore near-full-page images with no overlapping text (likely decorative backgrounds).
      - Capture ALL other images including author/editor photos, diagrams, etc.
      - Save each unique image XREF only once into SharedImages/, dedupe by xref.
      - For every placement (rect) create a <media> entry with its own coordinates
        but file pointing to SharedImages/<img_xrefN.ext>.

    Args:
        content_area: Optional rect defining the content area. Images outside this area
                      (in headers, footers, margins) will be skipped.
        full_page_threshold: Percentage of page area (0.0-1.0) above which an image is 
                            considered full-page decorative (default: 0.85 = 85%)

    Returns:
      List of raster image bounding rectangles (for use in vector deduplication).
    """
    images = page.get_images(full=True)
    img_counter = 0
    extracted_rects: List[fitz.Rect] = []
    page_rect = page.rect
    page_area = page_rect.width * page_rect.height

    for img in images:
        xref = img[0]
        rects = page.get_image_rects(xref)
        for rect in rects:
            if rect.width < min_size or rect.height < min_size:
                continue

            # Skip images outside the content area (in headers, footers, margins)
            # This handles logos, page numbers, running headers/footers
            if content_area is not None and not is_in_content_area(rect, content_area, min_overlap_pct=0.5):
                continue

            # FILTER: Skip full-page decorative images (backgrounds, watermarks)
            # Check if image covers most of the page (>85% by default)
            image_area = rect.width * rect.height
            if page_area > 0:
                coverage_ratio = image_area / page_area
                if coverage_ratio > full_page_threshold:
                    # Additional check: if image has significant text overlay, it's not just decorative
                    overlapping_text = sum(1 for blk in blocks if rect.intersects(blk["bbox"]))
                    # If very little text overlaps, it's likely a decorative background
                    if overlapping_text < 3:  # Less than 3 text blocks overlay
                        continue  # Skip full-page decorative image

            # ALL OTHER IMAGES ARE CAPTURED
            # This includes:
            # - Author/editor photos (no figure caption)
            # - Diagrams and illustrations
            # - Charts and graphs
            # - Icons and symbols
            # - Any image within content area that isn't full-page decorative

            # Now save the image (only if it passed the filters above)
            img_counter += 1
            filename = f"page{page_no}_img{img_counter}.png"
            out_path = os.path.join(media_dir, filename)

            pix = page.get_pixmap(clip=rect, dpi=dpi)
            pix.save(out_path)
            
            # Register in reference mapper for page-to-chapter tracking
            if HAS_REFERENCE_MAPPER:
                try:
                    mapper = get_mapper()
                    mapper.add_resource(
                        original_path=filename,
                        intermediate_name=filename,
                        resource_type="image",
                        first_seen_in=f"page_{page_no}",
                        width=int(rect.width),
                        height=int(rect.height),
                        is_raster=True,
                    )
                except Exception as e:
                    print(f"Warning: Failed to register image in mapper: {e}")

            # Track this rectangle for vector deduplication
            extracted_rects.append(rect)

            # Title / caption (but don't let caption become an entire column)
            title, caption = find_title_caption_for_region(rect, blocks)
            links = get_links_overlapping_rect(page, rect)

            media_el = ET.SubElement(
                page_el,
                "media",
                {
                    "id": f"p{page_no}_img{img_counter}",
                    "type": "raster",
                    "file": filename,
                    "x1": str(rect.x0),
                    "y1": str(rect.y0),
                    "x2": str(rect.x1),
                    "y2": str(rect.y1),
                    "alt": "",  # Placeholder for true /Alt text, if you ever add it
                    "title": sanitize_xml_text(title or ""),
                },
            )

            if caption:
                cap_el = ET.SubElement(media_el, "caption")
                cap_el.text = sanitize_xml_text(caption)

            for uri in links:
                ET.SubElement(media_el, "link", {"href": uri})

    return extracted_rects


# ----------------------------
# Vector drawing extraction (using cluster_drawings)
# ----------------------------

def extract_vector_blocks_for_page(
    page: fitz.Page,
    page_no: int,
    blocks: List[Dict[str, Any]],
    spans: List[Dict[str, Any]],
    media_dir: str,
    page_el: ET.Element,
    table_rects: Optional[List[fitz.Rect]] = None,
    raster_rects: Optional[List[fitz.Rect]] = None,
    content_area: Optional[fitz.Rect] = None,
    dpi: int = 200,
    min_size: float = 30.0,
    overlap_iou_thresh: float = 0.3,
) -> None:
    """
    Extract vector drawings from the page and combine fragmented pieces.

    This function now merges nearby drawing clusters to avoid fragmentation
    of complex diagrams that were split into multiple small pieces.

    Also detects complex drawing shapes (circles, ovals, arrows, curves) and
    captures them as images even if they're text-heavy, since diagrams often
    contain embedded text labels.

    Args:
        page: The fitz.Page object to extract from
        page_no: Page number (1-indexed)
        blocks: Text blocks from the page
        spans: Text spans from the page (for text-heavy detection)
        media_dir: Directory to save extracted images
        page_el: XML element to add media elements to
        table_rects: List of table bounding rectangles to avoid duplicate captures
        raster_rects: List of raster image bounding rectangles to avoid duplicate captures
        content_area: Optional rect defining the content area. Vectors outside this area
                      (in headers, footers, margins) will be skipped.
        dpi: Resolution for rendering
        min_size: Minimum size for vector clusters
        overlap_iou_thresh: IoU threshold for overlap detection with tables/raster images
    """
    if table_rects is None:
        table_rects = []
    if raster_rects is None:
        raster_rects = []
    drawings = page.get_drawings()
    if not drawings:
        return

    # cluster_drawings returns a list of bounding rects for grouped drawings
    try:
        clusters = page.cluster_drawings(drawings=drawings)
    except TypeError:
        # Fallback for older PyMuPDF without cluster_drawings(drawings=...)
        clusters = page.cluster_drawings()

    # Filter very small clusters and clusters outside content area
    clustered_rects = []
    for r in clusters:
        if r.width < min_size or r.height < min_size:
            continue
        # Skip vectors outside the content area (in headers, footers, margins)
        if content_area is not None and not is_in_content_area(r, content_area, min_overlap_pct=0.5):
            continue
        clustered_rects.append(r)

    vec_counter = 0
    for rect in clustered_rects:
        # 1) Skip vector blocks that overlap with table areas (already captured by Camelot)
        # Use a lower IoU threshold (0.15) to be more aggressive about excluding tables
        table_iou_thresh = 0.15
        if any(rect_iou(rect, t_rect) > table_iou_thresh for t_rect in table_rects):
            continue

        # 1a) Skip vector if it intersects ANY table rect significantly
        # Even partial overlap suggests this vector is part of a table
        skip_due_to_table = False
        for t_rect in table_rects:
            if rect.intersects(t_rect):
                # Calculate intersection area
                x_overlap = max(0, min(rect.x1, t_rect.x1) - max(rect.x0, t_rect.x0))
                y_overlap = max(0, min(rect.y1, t_rect.y1) - max(rect.y0, t_rect.y0))
                intersection_area = x_overlap * y_overlap
                vector_area = rect.width * rect.height
                table_area = t_rect.width * t_rect.height

                # Skip if >10% of vector overlaps with table OR >10% of table overlaps with vector
                if vector_area > 0 and (intersection_area / vector_area) > 0.1:
                    skip_due_to_table = True
                    break
                if table_area > 0 and (intersection_area / table_area) > 0.1:
                    skip_due_to_table = True
                    break
        if skip_due_to_table:
            continue

        # 1b) Skip vector if it looks like a table (grid of horizontal/vertical lines)
        # This catches tables that Camelot missed or that have slight bbox differences
        if is_table_like_drawing_region(rect, drawings):
            # print(f"    Page {page_no}: Skipping table-like vector region at {rect}")
            continue

        # 1c) Skip vector blocks that overlap with raster images (already captured)
        # This prevents capturing border rectangles around images as separate vectors
        if any(rect_iou(rect, r_rect) > overlap_iou_thresh for r_rect in raster_rects):
            continue

        # 1d) Skip vector if ANY raster image overlaps with this vector region
        # This handles cases where Figure label + multiple raster images form a large vector block
        # If rasters already captured the content, no need to capture the vector
        skip_vector = False
        skip_reason = ""
        for r_idx, r_rect in enumerate(raster_rects, 1):
            # Check if raster is fully or partially contained in vector region
            if r_rect.intersects(rect):
                # Calculate intersection area vs raster area
                x_overlap = max(0, min(rect.x1, r_rect.x1) - max(rect.x0, r_rect.x0))
                y_overlap = max(0, min(rect.y1, r_rect.y1) - max(rect.y0, r_rect.y0))
                intersection_area = x_overlap * y_overlap
                raster_area = r_rect.width * r_rect.height
                overlap_pct = (intersection_area / raster_area) * 100 if raster_area > 0 else 0
                
                # If > 20% of the raster is within this vector region, skip the vector
                # This catches cases where vector bbox includes raster images + labels
                if raster_area > 0 and (intersection_area / raster_area) > 0.2:
                    skip_vector = True
                    skip_reason = f"contains raster image #{r_idx} ({overlap_pct:.1f}% overlap)"
                    break
        
        if skip_vector:
            # Optional: Uncomment for debugging
            # print(f"    Page {page_no}: Skipping vector region - {skip_reason}")
            continue

        # 2) Check if region contains complex drawing shapes (circles, ovals, arrows, etc.)
        #    These indicate it's a diagram/figure worth capturing
        has_complex_shapes = has_complex_drawing_shapes(rect, drawings)

        # 3) Determine if this is text-heavy (mostly text, not a diagram)
        is_text_heavy = is_text_heavy_region(rect, spans)

        # 4) RELAXED FILTER: Capture vectors that are likely figures/diagrams
        #    - Keep if has complex drawing shapes (circles, arrows, diagrams)
        #    - Keep if NOT text-heavy (likely a simple vector graphic)
        #    - Skip ONLY if text-heavy AND no complex shapes (pure text box)
        #
        # This allows capturing:
        # - Diagrams with or without "Figure X" captions
        # - Simple vector graphics (borders, decorations around images)
        # - Charts and graphs
        # - Author/editor photo borders
        #
        # This skips:
        # - Pure text boxes (no drawing elements)
        if is_text_heavy and not has_complex_shapes:
            continue

        # 7) Expand bounding box to include nearby text labels that are part of the diagram
        #    This fixes the issue where flowchart labels and diagram text get cropped
        expanded_rect = expand_rect_for_nearby_text(rect, spans, max_distance=15.0)

        vec_counter += 1
        filename = f"page{page_no}_vector{vec_counter}.png"
        out_path = os.path.join(media_dir, filename)

        # Render using expanded rect to capture associated text
        pix = page.get_pixmap(clip=expanded_rect, dpi=dpi)
        pix.save(out_path)
        
        # Register in reference mapper for page-to-chapter tracking
        if HAS_REFERENCE_MAPPER:
            try:
                mapper = get_mapper()
                mapper.add_resource(
                    original_path=filename,
                    intermediate_name=filename,
                    resource_type="image",
                    first_seen_in=f"page_{page_no}",
                    width=int(expanded_rect.width),
                    height=int(expanded_rect.height),
                    is_vector=True,
                )
            except Exception as e:
                print(f"Warning: Failed to register vector in mapper: {e}")

        # Use expanded rect for metadata and caption detection
        title, caption = find_title_caption_for_region(expanded_rect, blocks)
        links = get_links_overlapping_rect(page, expanded_rect)

        media_el = ET.SubElement(
            page_el,
            "media",
            {
                "id": f"p{page_no}_vector{vec_counter}",
                "type": "vector",
                "file": filename,
                "x1": str(expanded_rect.x0),
                "y1": str(expanded_rect.y0),
                "x2": str(expanded_rect.x1),
                "y2": str(expanded_rect.y1),
                "alt": "",
                "title": sanitize_xml_text(title or ""),
            },
        )

        if caption:
            cap_el = ET.SubElement(media_el, "caption")
            cap_el.text = sanitize_xml_text(caption)

        for uri in links:
            ET.SubElement(media_el, "link", {"href": uri})


# ----------------------------
# Table extraction + XML
# ----------------------------

def detect_table_keywords_on_page(page: fitz.Page) -> List[Tuple[str, fitz.Rect]]:
    """
    Detect 'Table X.' patterns on a page.
    Returns list of (caption_text, rect) tuples for each detected table reference.

    Patterns matched:
    - "Table 1."
    - "Table 2:"
    - "Table A."
    - "Table I."
    etc.
    """
    import re

    results = []
    blocks = get_text_blocks(page)

    # Pattern: "Table" followed by number/letter, followed by period or colon
    # Captures the full caption line(s) after "Table X."
    pattern = re.compile(
        r'\b[Tt]able\s+([0-9]+|[A-Z]|[IVX]+)[\.:]\s*([^\n]*)',
        re.IGNORECASE
    )

    for block in blocks:
        text = block["text"]
        matches = pattern.finditer(text)

        for match in matches:
            table_num = match.group(1)
            caption_rest = match.group(2).strip()

            # Construct full caption (e.g., "Table 1. Summary of results")
            full_caption = f"Table {table_num}. {caption_rest}".strip()

            results.append((full_caption, block["bbox"]))

    return results


def is_valid_table(
    table: Any,
    min_accuracy: float = 60.0,
    min_rows: int = 2,
    min_cols: int = 2,
    min_area: float = 5000.0,
) -> bool:
    """
    Validate if a Camelot-detected table is actually a real table.

    Filters out false positives by checking:
    - Accuracy score (Camelot's confidence)
    - Minimum dimensions (rows x columns)
    - Minimum area (to avoid tiny fragments)
    - Data quality (non-empty cells)
    - Detects and rejects bullet lists disguised as tables
    """
    # Check accuracy threshold
    if hasattr(table, 'accuracy') and table.accuracy < min_accuracy:
        return False

    # Check minimum dimensions
    df = table.df
    rows, cols = df.shape
    if rows < min_rows or cols < min_cols:
        return False

    # Check minimum area (bbox size)
    x1, y1, x2, y2 = table._bbox
    area = (x2 - x1) * (y2 - y1)
    if area < min_area:
        return False

    # Check if table has meaningful content (at least some non-empty cells)
    non_empty_cells = df.astype(str).apply(lambda x: x.str.strip() != '').sum().sum()
    total_cells = rows * cols
    if total_cells > 0 and non_empty_cells / total_cells < 0.1:  # Less than 10% filled
        return False

    # CRITICAL: Detect and reject bullet lists disguised as tables
    # Bullet lists often get detected as 2-column tables with:
    # - First column: bullet character (•, -, *, etc.)
    # - Second column: list item text
    # Check if this looks like a bullet list
    if cols == 2:
        # Get first column content
        first_col = df.iloc[:, 0].astype(str).str.strip()
        
        # Count how many cells in first column are single bullet characters
        bullet_chars = {'•', '●', '○', '■', '□', '▪', '▫', '·', '-', '*', '–', '—'}
        bullet_count = sum(1 for val in first_col if val in bullet_chars or len(val) <= 1)
        
        # If > 70% of first column is bullets, this is likely a bullet list
        if bullet_count / len(first_col) > 0.7:
            return False
        
        # Also check if first column is very narrow compared to second column
        # (typical of bullet list layouts)
        first_col_width = abs(x2 - x1) * 0.15  # Assume first col is ~15% or less
        if first_col_width < 30:  # Less than 30 points wide
            # Check if many cells in first column are very short
            short_content_count = sum(1 for val in first_col if len(val) <= 2)
            if short_content_count / len(first_col) > 0.6:
                return False

    return True


def extract_tables(
    pdf_path: str,
    doc: fitz.Document,
) -> Tuple[Dict[int, List[Any]], Dict[int, List[str]]]:
    """
    Use Camelot to read tables, but ONLY on pages that contain 'Table X.' keywords.
    Returns (tables_by_page, captions_by_page):
      - tables_by_page: {page_no: [table, ...]}
      - captions_by_page: {page_no: [caption1, caption2, ...]}

    Uses ONLY stream flavor for table detection:
    - stream: works for both bordered and borderless tables
    - lattice flavor is DISABLED to avoid duplicates

    Applies strict filtering to reduce false positives:
    - Bullet list detection (rejects 2-column bullet lists)
    - Minimum size and accuracy thresholds
    - Deduplication for tables detected multiple times
    """
    # You can tweak flavor='lattice'/'stream' depending on your PDFs
    tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream", strip_text="\n")
    tables_by_page: Dict[int, List[Any]] = {}
    captions_by_page: Dict[int, List[str]] = {}

    # Step 1: Scan all pages for "Table X." keywords
    print("  Scanning pages for 'Table X.' keywords...")
    pages_with_tables = set()
    for page_index in range(len(doc)):
        page_no = page_index + 1
        page = doc[page_index]
        table_refs = detect_table_keywords_on_page(page)

        if table_refs:
            pages_with_tables.add(page_no)
            # Store captions WITH positions for this page (for proximity matching)
            captions_by_page[page_no] = table_refs  # List of (caption, rect) tuples
            print(f"    Page {page_no}: Found {len(table_refs)} table reference(s)")

    if not pages_with_tables:
        print("  No 'Table X.' keywords found in document. Skipping Camelot detection.")
        return tables_by_page, captions_by_page

    # Convert page numbers to comma-separated string for Camelot
    pages_str = ",".join(str(p) for p in sorted(pages_with_tables))
    print(f"  Running Camelot on {len(pages_with_tables)} page(s) with table keywords: {pages_str}")

    # DISABLED: Lattice flavor (for bordered tables)
    # Using only stream flavor as per user request
    # try:
    #     lattice_tables = camelot.read_pdf(
    #         pdf_path,
    #         pages=pages_str,
    #         flavor="lattice",
    #         strip_text="\n",
    #     )
    #     print(f"  Lattice flavor detected {len(lattice_tables)} candidates")
    #
    #     # Filter valid tables
    #     valid_count = 0
    #     for t in lattice_tables:
    #         if is_valid_table(t):
    #             page_no = int(t.page)
    #             tables_by_page.setdefault(page_no, []).append(t)
    #             valid_count += 1
    #
    #     print(f"  Lattice flavor: {valid_count} valid tables after filtering")
    # except Exception as e:
    #     print(f"  Lattice flavor failed: {e}")

    # Use stream flavor ONLY (lattice disabled to avoid duplicates)
    # With bullet list detection and validation
    try:
        stream_tables = camelot.read_pdf(
            pdf_path,
            pages=pages_str,
            flavor="stream",
            strip_text="\n",
        )
        print(f"  Stream flavor detected {len(stream_tables)} candidates")

        # Filter valid tables and avoid duplicates
        # (Deduplication still needed as stream can detect same table multiple times)
        valid_count = 0
        skipped_duplicates = 0
        for t in stream_tables:
            # Apply validation to filter out false positives
            if not is_valid_table(t, min_accuracy=70.0, min_rows=3, min_cols=2):
                continue

            page_no = int(t.page)
            t_rect = camelot_bbox_to_fitz_rect(t._bbox, doc[page_no - 1].rect.height)

            # Check if this table overlaps with already-accepted tables on same page
            # Camelot stream can sometimes detect the same table multiple times
            is_duplicate = False
            if page_no in tables_by_page:
                for existing_t in tables_by_page[page_no]:
                    existing_rect = camelot_bbox_to_fitz_rect(
                        existing_t._bbox,
                        doc[page_no - 1].rect.height
                    )
                    
                    # Check IoU (Intersection over Union)
                    iou = rect_iou(t_rect, existing_rect)
                    
                    # Also check if centers are very close (indicates same table)
                    t_center_x = (t_rect.x0 + t_rect.x1) / 2
                    t_center_y = (t_rect.y0 + t_rect.y1) / 2
                    existing_center_x = (existing_rect.x0 + existing_rect.x1) / 2
                    existing_center_y = (existing_rect.y0 + existing_rect.y1) / 2
                    
                    center_distance = ((t_center_x - existing_center_x) ** 2 + 
                                     (t_center_y - existing_center_y) ** 2) ** 0.5
                    
                    # Consider duplicate if:
                    # 1. IoU > 0.5 (50% overlap)
                    # 2. OR centers are within 50 pixels and there's any overlap (IoU > 0.1)
                    if iou > 0.5 or (center_distance < 50 and iou > 0.1):
                        is_duplicate = True
                        skipped_duplicates += 1
                        break

            if not is_duplicate:
                tables_by_page.setdefault(page_no, []).append(t)
                valid_count += 1

        print(f"  Stream flavor: {valid_count} valid tables after filtering and deduplication")
        if skipped_duplicates > 0:
            print(f"  Stream flavor: Skipped {skipped_duplicates} duplicate tables")
    except Exception as e:
        print(f"  Stream flavor failed: {e}")

    total_tables = sum(len(tables) for tables in tables_by_page.values())
    print(f"  Total valid tables detected: {total_tables}")

    return tables_by_page, captions_by_page


def add_tables_for_page(
    pdf_path: str,
    doc: fitz.Document,
    page: fitz.Page,
    page_no: int,
    tables_for_page: List[Any],
    blocks: List[Dict[str, Any]],
    spans: List[Dict[str, Any]],
    media_dir: str,
    page_el: ET.Element,
    extracted_captions: List[Tuple[str, fitz.Rect]] = None,
    dpi: int = 200,
    require_table_caption: bool = True,
    max_caption_distance: float = 100.0,
) -> None:
    """
    For each Camelot table on this page:
      - compute region rect in PyMuPDF coords
      - validate table has a "Table X" caption nearby (if require_table_caption=True)
      - Match captions to tables by PROXIMITY, not by index
      - add <table> element with bbox (NO PNG rendering - bounds are unreliable)
      - add per-cell bbox + spans (font, size, color, text)
      - attach title/caption/links from extracted 'Table X.' keywords.

    Args:
        extracted_captions: List of (caption_text, rect) tuples from 'Table X.' keywords on this page.
                           Captions are matched to tables by PROXIMITY, not by index.
        require_table_caption: If True, skip tables that don't have a "Table X" caption nearby.
                               This helps filter out false positives from Camelot.
        max_caption_distance: Maximum distance (in points) between table and caption for a match.
    """
    page_height = page.rect.height
    tables_added = 0
    tables_skipped = 0

    # Track which captions have been used to avoid duplicate assignment
    used_captions = set()

    for idx, t in enumerate(tables_for_page, start=1):
        bbox_pdf = t._bbox  # (x1, y1, x2, y2) bottom-left origin
        table_rect = camelot_bbox_to_fitz_rect(bbox_pdf, page_height)

        # PNG rendering removed - table bounds are often incorrect
        # Table data is preserved in cell-level XML structure below

        # Find the closest caption to this table by PROXIMITY (not index)
        caption = ""
        best_distance = None

        if extracted_captions:
            for cap_idx, (cap_text, cap_rect) in enumerate(extracted_captions):
                # Skip already-used captions
                if cap_idx in used_captions:
                    continue

                # Calculate distance between table and caption
                # Caption can be above or below the table
                dist = None

                # Check if caption is ABOVE the table
                if cap_rect.y1 <= table_rect.y0:
                    dist = table_rect.y0 - cap_rect.y1

                # Check if caption is BELOW the table
                elif cap_rect.y0 >= table_rect.y1:
                    dist = cap_rect.y0 - table_rect.y1

                # Check horizontal overlap (caption should be horizontally aligned with table)
                if dist is not None:
                    h_overlap = min(table_rect.x1, cap_rect.x1) - max(table_rect.x0, cap_rect.x0)
                    if h_overlap < 0:
                        # No horizontal overlap - penalize heavily
                        dist += 500

                # Skip if too far
                if dist is None or dist > max_caption_distance:
                    continue

                # Keep the closest match
                if best_distance is None or dist < best_distance:
                    best_distance = dist
                    caption = cap_text
                    best_cap_idx = cap_idx

        # Mark caption as used if found
        if caption and best_distance is not None:
            used_captions.add(best_cap_idx)
        else:
            # Fallback: Look for "Table X" pattern near this specific table using text blocks
            caption = find_table_caption(table_rect, blocks, max_distance=60.0, require_table_pattern=True)

        # Skip tables without a valid "Table X" caption (likely false detection)
        if require_table_caption and not caption:
            tables_skipped += 1
            print(f"    Page {page_no}: Skipping table {idx} (bbox: {table_rect.x0:.1f},{table_rect.y0:.1f},{table_rect.x1:.1f},{table_rect.y1:.1f}) - no 'Table X' caption found within {max_caption_distance} points")
            continue

        tables_added += 1
        title = caption  # Use caption as title

        links = get_links_overlapping_rect(page, table_rect)

        table_el = ET.SubElement(
            page_el,
            "table",
            {
                "id": f"p{page_no}_table{idx}",
                "x1": str(table_rect.x0),
                "y1": str(table_rect.y0),
                "x2": str(table_rect.x1),
                "y2": str(table_rect.y1),
                "title": sanitize_xml_text(title or ""),
                "alt": "",  # Placeholder – true /Alt text for tagged tables is not exposed here
            },
        )

        if caption:
            cap_el = ET.SubElement(table_el, "caption")
            cap_el.text = sanitize_xml_text(caption)

        for uri in links:
            ET.SubElement(table_el, "link", {"href": uri})

        # ---- Per-cell bounding boxes + spans ----
        cells = t.cells  # 2D list [row][col]
        nrows = len(cells)
        ncols = len(cells[0]) if nrows > 0 else 0

        # Spans: list of {"text","bbox":(x0,y0,x1,y1),"font","size","color"}
        # We'll assign a span to a cell if its center lies inside the cell rect
        def spans_for_rect(cell_rect: fitz.Rect) -> List[Dict[str, Any]]:
            cell_spans: List[Dict[str, Any]] = []
            for s in spans:
                x0, y0, x1, y1 = s["bbox"]
                s_rect = fitz.Rect(x0, y0, x1, y1)
                if not s_rect.intersects(cell_rect):
                    continue
                cx = (x0 + x1) / 2.0
                cy = (y0 + y1) / 2.0
                if not cell_rect.contains(fitz.Point(cx, cy)):
                    continue
                cell_spans.append(s)
            return cell_spans

        rows_el = ET.SubElement(table_el, "rows")
        for r_idx in range(nrows):
            row_el = ET.SubElement(rows_el, "row", {"index": str(r_idx)})
            for c_idx in range(ncols):
                cell = cells[r_idx][c_idx]
                # Camelot cell bbox in PDF coords
                cbbox_pdf = (cell.x1, cell.y1, cell.x2, cell.y2)
                cell_rect = camelot_bbox_to_fitz_rect(cbbox_pdf, page_height)

                cell_el = ET.SubElement(
                    row_el,
                    "cell",
                    {
                        "index": str(c_idx),
                        "x1": str(cell_rect.x0),
                        "y1": str(cell_rect.y0),
                        "x2": str(cell_rect.x1),
                        "y2": str(cell_rect.y1),
                    },
                )

                # Attach spans as <chunk>
                cell_spans = spans_for_rect(cell_rect)
                for s in cell_spans:
                    chunk_el = ET.SubElement(
                        cell_el,
                        "chunk",
                        {
                            "font": sanitize_xml_text(s["font"]),
                            "size": str(s["size"]),
                            "color": s["color"],
                        },
                    )
                    chunk_el.text = sanitize_xml_text(s["text"])

    # Log summary for this page
    if tables_added > 0 or tables_skipped > 0:
        print(f"    Page {page_no}: Added {tables_added} table(s), skipped {tables_skipped} table(s)")


# ----------------------------
# Main driver
# ----------------------------

def extract_media_and_tables(
    pdf_path: str,
    out_dir: str | None = None,
    dpi: int = 200,
    require_table_caption: bool = True,
    max_caption_distance: float = 100.0,
) -> str:
    """
    Extracts:
      - raster images (ALL images except full-page decorative and header/footer logos)
      - vector drawing snapshots (clustered into full blocks)
      - tables + per-cell bboxes + spans

    Image Filtering Rules:
      - CAPTURE: All images in content area (author photos, figures, diagrams, etc.)
      - SKIP: Images in headers/footers/margins (logos, page numbers, running headers)
      - SKIP: Full-page decorative images (backgrounds, watermarks covering >85% of page)

    Table Filtering:
      - If require_table_caption=True, only tables with "Table X" captions are kept
      - If require_table_caption=False, all Camelot detections are kept (may include false positives)
      - max_caption_distance controls how far caption can be from table (in points)

    Args:
        pdf_path: Path to input PDF
        out_dir: Optional output directory for media files
        dpi: DPI for rendering images
        require_table_caption: If True, filter out tables without "Table X" captions (default: True)
        max_caption_distance: Maximum distance between table and caption in points (default: 100.0)

    Saves:
      - All PNGs into <basename>_MultiMedia/
      - XML metadata into <basename>_MultiMedia.xml

    Returns path to XML file.
    """
    pdf_path = os.path.abspath(pdf_path)
    base_dir = os.path.dirname(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    # Output folder: <inputfile>_MultiMedia
    media_dir = out_dir or os.path.join(base_dir, f"{base_name}_MultiMedia")
    ensure_dir(media_dir)

    xml_path = os.path.join(base_dir, f"{base_name}_MultiMedia.xml")

    doc = fitz.open(pdf_path)
    root = ET.Element("document", {"source": os.path.basename(pdf_path)})

    print("Running table detection with Camelot...")
    tables_by_page, captions_by_page = extract_tables(pdf_path, doc)
    print("Table detection done.")

    num_pages = len(doc)
    print(f"Processing {num_pages} pages...")

    for page_index in range(num_pages):
        page_no = page_index + 1
        page = doc[page_index]
        page_rect = page.rect

        page_el = ET.SubElement(
            root,
            "page",
            {
                "index": str(page_no),
                "width": str(page_rect.width),
                "height": str(page_rect.height),
            },
        )

        # Calculate content area (excludes headers, footers, and margins)
        # This prevents capturing logos, page numbers, and decorative elements
        content_area = get_content_area_rect(
            page_rect,
            header_margin_pct=0.08,   # Skip top 8% (header area)
            footer_margin_pct=0.08,   # Skip bottom 8% (footer area)
            left_margin_pct=0.05,     # Skip left 5% (margin)
            right_margin_pct=0.05,    # Skip right 5% (margin)
        )

        # Collect text blocks once (for caption / title heuristics)
        blocks = get_text_blocks(page)
        # Collect detailed spans once (for cell-level chunks)
        spans = get_page_spans(page)

        # Raster images - get rectangles for deduplication with vectors
        page_raster_rects = extract_raster_images_for_page(
            page=page,
            page_no=page_no,
            blocks=blocks,
            media_dir=media_dir,
            page_el=page_el,
            content_area=content_area,
            dpi=dpi,
        )

        # Compute table bounding rects for this page (to avoid duplicate captures)
        page_table_rects: List[fitz.Rect] = []
        if page_no in tables_by_page:
            page_height = page_rect.height
            for t in tables_by_page[page_no]:
                t_rect = camelot_bbox_to_fitz_rect(t._bbox, page_height)
                page_table_rects.append(t_rect)

        # Vector drawings (clustered) - skip areas already captured as raster/table
        extract_vector_blocks_for_page(
            page=page,
            page_no=page_no,
            blocks=blocks,
            spans=spans,
            media_dir=media_dir,
            page_el=page_el,
            table_rects=page_table_rects,
            raster_rects=page_raster_rects,
            content_area=content_area,
            dpi=dpi,
        )

        # Tables on this page (if any)
        if page_no in tables_by_page:
            # Get extracted captions for this page
            page_captions = captions_by_page.get(page_no, [])

            add_tables_for_page(
                pdf_path=pdf_path,
                doc=doc,
                page=page,
                page_no=page_no,
                tables_for_page=tables_by_page[page_no],
                blocks=blocks,
                spans=spans,
                media_dir=media_dir,
                page_el=page_el,
                extracted_captions=page_captions,
                dpi=dpi,
                require_table_caption=require_table_caption,
                max_caption_distance=max_caption_distance,
            )

        # Progress reporting
        if page_no == 1 or page_no % 10 == 0 or page_no == num_pages:
            print(f"  Processed page {page_no}/{num_pages}")
        
        # Aggressive garbage collection every 50 pages to free memory
        # This is critical for large PDFs (500+ pages) to avoid memory accumulation
        if page_no % 50 == 0:
            gc.collect()
            print(f"  [Memory cleanup after page {page_no}]")

    doc.close()

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")  # Python 3.9+
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)

    # Count tables in final XML
    total_tables_in_xml = len(root.findall('.//table'))
    total_tables_detected = sum(len(tables) for tables in tables_by_page.values())
    
    print(f"\n{'='*60}")
    print(f"Table Extraction Summary:")
    print(f"  Total tables detected by Camelot: {total_tables_detected}")
    print(f"  Total tables written to media.xml: {total_tables_in_xml}")
    if total_tables_in_xml < total_tables_detected:
        print(f"  Tables filtered out: {total_tables_detected - total_tables_in_xml}")
        print(f"  Reason: No 'Table X' caption found within 100 points")
        print(f"  Tip: Check the detailed logs above to see which tables were skipped")
    print(f"{'='*60}\n")
    
    print(f"XML metadata written to: {xml_path}")
    print(f"Media saved under: {media_dir}")
    return xml_path


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extract all media (raster images, vector drawing blocks, tables with per-cell bboxes/spans) "
            "from a PDF into <input>_MultiMedia/ + XML metadata."
        )
    )
    parser.add_argument("pdf_path", help="Path to input PDF")
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Render dpi for PNG snapshots (default: 200)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional override for multimedia folder. "
             "Default: <inputfile>_MultiMedia in the same directory.",
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

    extract_media_and_tables(
        pdf_path=args.pdf_path,
        out_dir=args.out,
        dpi=args.dpi,
        require_table_caption=not args.no_caption_filter,
        max_caption_distance=args.caption_distance,
    )


if __name__ == "__main__":
    main()
