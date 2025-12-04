# Code Review Analysis

## Date: November 25, 2025

## Issues Identified

### 1. TOC.xml Capture Issue ⚠️

**Location**: `heuristics_Nov3.py`, lines 2230-2262

**Problem**: 
- TOC capture starts correctly when "Table of Contents" heading is detected
- However, it **does NOT stop** when it encounters the next text element with same/bigger font size
- Currently captures everything from TOC start all the way to the end of the book

**Current Logic**:
```python
# Line 2230-2262
if TOC_RE.match(text.lower()) and _has_heading_font(line, body_size):
    # Creates a block with label "toc"
    blocks.append({
        "label": "toc",
        "text": combined_text,
        ...
    })
    # Sets flags but does NOT track TOC content collection
    front_matter_mode = False
    front_matter_locked = True
    idx = next_idx
    continue  # Just continues processing without TOC boundary tracking
```

**What's Missing**:
- No `in_toc_section` flag (unlike Index which has `in_index_section`)
- No font size comparison to detect when TOC ends
- No mechanism to stop collecting TOC entries

**Fix Needed**:
1. Add `in_toc_section` flag
2. Store TOC heading font size
3. After TOC heading, collect entries until:
   - Text element has font size >= TOC heading font size
   - OR a chapter/section heading is detected
4. When boundary is found, set `in_toc_section = False`

---

### 2. Vector Image Capture Logic 📊

**Location**: `Multipage_Image_Extractor.py`, lines 578-705

**Current Rules** (in order):

#### Step 1: Raster Image Extraction (lines 488-571)
```python
def extract_raster_images_for_page():
    """
    Extracts all raster images from page.
    - Saves each image with position coordinates
    - Returns list of bounding rectangles
    """
    # For each image:
    # 1. Check minimum size (min_size=5.0)
    # 2. Check if small icon (< 100px)
    # 3. Apply keyword filtering (unless small icon)
    # 4. Track rectangle for vector deduplication
    return extracted_rects
```

**Raster Rules**:
- ✅ Extract all raster images with position coordinates
- ✅ Small images (<100px) bypass keyword filtering (treated as inline icons)
- ✅ Large images require figure keywords nearby
- ✅ Position rectangles stored for vector deduplication

#### Step 2: Vector Drawing Extraction (lines 578-705)
```python
def extract_vector_blocks_for_page(
    page, blocks, spans, 
    table_rects,      # From table detection
    raster_rects,     # From raster extraction above
):
    """
    Extracts vector drawings using cluster_drawings().
    - Merges nearby drawing clusters
    - Filters based on overlaps and content
    """
```

**Vector Rules**:

1. **Overlap with Tables** (line 638):
   ```python
   if any(rect_iou(rect, t_rect) > 0.3 for t_rect in table_rects):
       continue  # Skip - already captured as table
   ```

2. **Overlap with Rasters** (line 643):
   ```python
   if any(rect_iou(rect, r_rect) > 0.3 for r_rect in raster_rects):
       continue  # Skip - already captured as raster
   ```

3. **Figure Keywords Check** (line 647):
   ```python
   has_keywords = has_figure_keywords_nearby(rect, blocks)
   # Looks for: "figure", "image", "table", "fig.", etc.
   # Within 100px above/below region
   ```

4. **Complex Shape Detection** (line 651):
   ```python
   has_complex_shapes = has_complex_drawing_shapes(rect, drawings)
   # Detects: circles, ovals, arrows, curves
   # See COMPLEX_SHAPE_DETECTION.md for details
   ```

5. **Text-Heavy Check** (line 654):
   ```python
   is_text_heavy = is_text_heavy_region(rect, spans)
   # Returns True if >150 chars OR >50% text coverage
   ```

6. **Decision Logic** (lines 660-665):
   ```python
   # FILTER 1: Skip if text-heavy without keywords/shapes
   if is_text_heavy and not has_keywords and not has_complex_shapes:
       continue
   
   # FILTER 2: Skip if no keywords AND no complex shapes
   if not has_keywords and not has_complex_shapes:
       continue
   
   # If we reach here: CAPTURE the vector
   ```

7. **Text Expansion** (line 669):
   ```python
   expanded_rect = expand_rect_for_nearby_text(rect, spans, max_distance=15.0)
   # Expands bbox to include diagram labels within 15px
   ```

---

## Current Vector Capture Rules Summary

| Condition | Keywords | Complex Shapes | Text-Heavy | Result |
|-----------|----------|----------------|------------|--------|
| 1 | ✅ Yes | ✅ Yes | ✅ Yes | ✅ CAPTURE |
| 2 | ✅ Yes | ✅ Yes | ❌ No | ✅ CAPTURE |
| 3 | ✅ Yes | ❌ No | ✅ Yes | ✅ CAPTURE |
| 4 | ✅ Yes | ❌ No | ❌ No | ✅ CAPTURE |
| 5 | ❌ No | ✅ Yes | ✅ Yes | ❌ SKIP (text-heavy filter) |
| 6 | ❌ No | ✅ Yes | ❌ No | ✅ CAPTURE |
| 7 | ❌ No | ❌ No | ✅ Yes | ❌ SKIP (both filters) |
| 8 | ❌ No | ❌ No | ❌ No | ❌ SKIP (no keywords/shapes) |

**Wait, there's a logic bug!** 

Row 5 shows: Complex shapes but text-heavy without keywords → SKIP

This seems wrong. If something has complex shapes (circles, arrows), it should be captured even if text-heavy and without explicit keywords.

**Current Code** (lines 660-661):
```python
if is_text_heavy and not has_keywords and not has_complex_shapes:
    continue
```

This correctly skips only if text-heavy AND no keywords AND no complex shapes.

**But then** (lines 664-665):
```python
if not has_keywords and not has_complex_shapes:
    continue
```

This means: If no keywords AND no complex shapes → skip.

**Combined Logic**:
- Vector is captured if: `has_keywords OR has_complex_shapes`
- UNLESS: `is_text_heavy AND not has_keywords AND not has_complex_shapes`

**Corrected Table**:

| Condition | Keywords | Complex Shapes | Text-Heavy | Result |
|-----------|----------|----------------|------------|--------|
| 1 | ✅ Yes | ✅ Yes | ✅ Yes | ✅ CAPTURE |
| 2 | ✅ Yes | ✅ Yes | ❌ No | ✅ CAPTURE |
| 3 | ✅ Yes | ❌ No | ✅ Yes | ✅ CAPTURE |
| 4 | ✅ Yes | ❌ No | ❌ No | ✅ CAPTURE |
| 5 | ❌ No | ✅ Yes | ✅ Yes | ✅ CAPTURE |
| 6 | ❌ No | ✅ Yes | ❌ No | ✅ CAPTURE |
| 7 | ❌ No | ❌ No | ✅ Yes | ❌ SKIP |
| 8 | ❌ No | ❌ No | ❌ No | ❌ SKIP |

**Simplified**:
- ✅ CAPTURE if: `has_keywords OR has_complex_shapes`
- ❌ SKIP if: no keywords AND no complex shapes

---

## Additional Rules Currently in Place

### Raster Deduplication
- **IoU Threshold**: 0.3 (30% overlap)
- **Logic**: If vector overlaps with raster by >30%, skip vector
- **Purpose**: Avoid capturing border rectangles around images

### Table Deduplication
- **IoU Threshold**: 0.3 (30% overlap)
- **Logic**: If vector overlaps with table by >30%, skip vector
- **Purpose**: Avoid duplicate capture of tabular data

### Minimum Sizes
- **Raster**: 5.0 pixels (width or height)
- **Vector**: 30.0 pixels (after clustering)

### Keyword Detection
- **Keywords**: "figure", "image", "table", "fig.", "fig ", "tbl.", "tbl "
- **Search Radius**: 100 pixels above/below
- **Horizontal Tolerance**: 50 pixels for alignment

### Complex Shape Detection
- **Curves**: 1+ bezier curves (circles, ovals, arcs)
- **Lines**: 3+ lines with ≤2 rectangles (arrows, connectors)
- **Quads**: 2+ quadrilaterals
- **Mixed**: 1+ curve + 2+ lines

---

## Questions for Clarification

### TOC.xml Issue
1. Should TOC collection stop immediately when seeing same/bigger font size?
2. Or should it allow some tolerance (e.g., ±2pt)?
3. Should we collect TOC entries as separate blocks or as a single chapter?

### Vector Image Rules
You mentioned a new logic:
> "If it has drawings and shapes beyond just lines (like circle, oval, arrows etc..) then check if there is a raster captured in the same vicinity in that page already (media xml of that page)? If there is a raster image captured from that page already and its position is within this vector bounds, then skip it."

**Current Implementation**:
- ✅ Already checks if raster is captured
- ✅ Skips vector if vector overlaps WITH raster (vector rect intersects raster rect)

**Your New Requirement**:
- Check if raster is within vector bounds (raster fully inside vector)
- This is the OPPOSITE check

**Question**: Do you want to change from:
- Current: Skip if `vector.intersects(raster)` with IoU > 0.3
- New: Skip if `vector.contains(raster)` fully

Or do you want BOTH checks?

### Other Rules
What other rules would you like to add or modify?

---

## Proposed Fixes

### Fix 1: TOC Collection with Font Size Boundary

Add to `heuristics_Nov3.py` around line 2230:

```python
# After TOC heading is detected
if TOC_RE.match(text.lower()) and _has_heading_font(line, body_size):
    # ... existing code to create TOC heading block ...
    
    # NEW: Track TOC mode and font size
    in_toc_section = True
    toc_heading_font_size = max(h.font_size for h in heading_lines if h.font_size)
    toc_entries = []  # Collect TOC entries
    
    idx = next_idx
    continue

# NEW: Inside the main loop, check if we're in TOC section
if in_toc_section and entry.get("kind") in ("line", "text"):
    # Check if this text has same or bigger font size
    if line.font_size >= toc_heading_font_size:
        # TOC section ends
        in_toc_section = False
        # Process collected TOC entries
        for toc_entry in toc_entries:
            blocks.append({
                "label": "index_item",  # Use same label as index
                "text": toc_entry.text,
                ...
            })
        toc_entries = []
        # Continue processing current line as normal
    else:
        # Still in TOC, collect this entry
        toc_entries.append(line)
        idx += 1
        continue
```

### Fix 2: Vector-Raster Containment Check

Modify `Multipage_Image_Extractor.py` around line 643:

```python
# Current check: vector overlaps with raster
if any(rect_iou(rect, r_rect) > overlap_iou_thresh for r_rect in raster_rects):
    continue

# NEW: Add containment check
# Skip if any raster is fully contained within this vector
if any(r_rect.x0 >= rect.x0 and r_rect.y0 >= rect.y0 and 
       r_rect.x1 <= rect.x1 and r_rect.y1 <= rect.y1 
       for r_rect in raster_rects):
    continue  # Raster already captured this region
```

---

## Files to Modify

1. **heuristics_Nov3.py** - Fix TOC collection logic
2. **Multipage_Image_Extractor.py** - Adjust vector-raster deduplication

## Testing Required

1. Process a PDF with Table of Contents
2. Verify TOC.xml stops at correct boundary
3. Verify vector images with embedded raster images are handled correctly
4. Check that diagrams with text labels are still captured
