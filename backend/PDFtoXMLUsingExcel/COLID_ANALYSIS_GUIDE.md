# ColId Weaving Analysis Guide

## Problem Description

On single-column pages with mixed content types (short headers, section headers, indented paragraphs, full-width paragraphs), the ColId assignment "weaves" between:
- **ColId 0**: Full-width content
- **ColId 1**: Column content

This creates issues in the reading order because the system treats ColId changes as major content transitions.

## Root Cause Analysis

### Current ColId Assignment Logic

The `assign_column_ids()` function in `pdf_to_excel_columns.py` (lines 579-640) uses these rules:

```python
# Rule 1: Full-width if spans both margins (within 5% tolerance)
if left <= left_margin and right >= right_margin:
    col_id = 0

# Rule 2: Full-width if width ≥ 45% of page width  
elif width >= page_width * 0.45:
    col_id = 0

# Rule 3: Otherwise assign to column based on left edge position
else:
    # Assign to column 1, 2, 3, etc. based on boundaries
    col_id = 1 (or 2, 3...)
```

### Why Weaving Occurs

On **single-column pages**:

1. **Short headers** (e.g., "Chapter 1") → Width < 45% → **ColId 1**
2. **Full paragraph** → Width ≥ 45% → **ColId 0** 
3. **Indented paragraph** → Width < 45% → **ColId 1**
4. **Full paragraph** → Width ≥ 45% → **ColId 0**
5. **Section header** (short) → Width < 45% → **ColId 1**

This creates a weaving pattern: `1 → 0 → 1 → 0 → 1 → 0`

### Impact on Reading Order

The `assign_reading_order_blocks()` function (lines 140-208) treats ColId changes as significant:

```python
# Block 1: Full-width content ABOVE columns (col_id=0)
# Block 2: Column 1 (col_id=1)
# Block 3: Column 2 (col_id=2)
# ...
# Block N: Full-width content BELOW columns (col_id=0)
```

When ColId weaves on a single-column page:
- Each transition creates a new ReadingOrderBlock
- This fragments continuous content into multiple blocks
- XML generation and paragraph detection break at block boundaries
- Result: Poor reading order and incorrect structure

## How to Diagnose

### Step 1: Generate Excel File

```bash
python pdf_to_excel_columns.py your_document.pdf
```

This creates `your_document_columns.xlsx` with ReadingOrder sheet.

### Step 2: Analyze Weaving Patterns

```bash
# Analyze all pages for weaving patterns
python analyze_colid_weaving.py your_document_columns.xlsx

# Analyze specific page in detail
python analyze_colid_weaving.py your_document_columns.xlsx --page 5

# Show detailed assignment logic for a page
python analyze_colid_weaving.py your_document_columns.xlsx --page 5 --logic
```

### Step 3: Review Output

The analysis shows:
- **ColId transitions**: Number of times ColId alternates between 0 and 1
- **Weaving detected**: YES if >3 transitions (indicates problem)
- **Detailed view**: Each fragment with its ColId, width, and assignment reason

Example output:

```
PAGE 5 - ColId Transition Analysis
================================================================================
Total fragments: 45
Page width: 612.0
ColId transitions (0↔1): 12
Weaving detected: YES

ColId sequence: [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, ...]

Fragments by ColId:
  ColId 0: 22 fragments
  ColId 1: 23 fragments

DETAILED COLID WEAVING ANALYSIS
────────────────────────────────────────────────────────────────────────────────
RO    Block   ColID   Left     Width    %Width   Text
────────────────────────────────────────────────────────────────────────────────
1     1       1       108.0    96.5     15.8%    Chapter 1 ← TRANSITION
2     1       0       72.0     468.0    76.5%    This is a full paragraph... ← TRANSITION
3     1       1       108.0    432.0    70.6%    This is indented paragraph ← TRANSITION
4     1       0       72.0     468.0    76.5%    Another full paragraph text ← TRANSITION
```

## Solutions

### Solution 1: Single-Column Page Detection

Add logic to detect truly single-column pages and skip the width-based rule:

```python
def is_single_column_page(fragments, col_starts):
    """
    Detect if a page is truly single-column.
    
    Criteria:
    - Only one column start detected
    - OR most fragments (>80%) are left-aligned to the same position
    - OR page has no fragments with ColId > 1
    """
    if len(col_starts) <= 1:
        return True
    
    # Check if >80% of fragments start at similar left position
    left_positions = [f["left"] for f in fragments]
    most_common_left = max(set(left_positions), key=left_positions.count)
    similar_left_count = sum(1 for left in left_positions if abs(left - most_common_left) < 20)
    
    if similar_left_count / len(fragments) > 0.8:
        return True
    
    return False

def assign_column_ids(fragments, page_width, col_starts):
    # Check if single-column page
    if is_single_column_page(fragments, col_starts):
        # Assign all to ColId 1 (or all to ColId 0)
        for f in fragments:
            f["col_id"] = 1
        return
    
    # ... existing multi-column logic ...
```

### Solution 2: Adjust Width Threshold

Increase the width threshold for ColId 0 assignment to reduce false positives:

```python
# Current: 45% of page width
elif width >= page_width * 0.45:
    f["col_id"] = 0

# Proposed: 60% of page width (more conservative)
elif width >= page_width * 0.60:
    f["col_id"] = 0
```

This reduces weaving but may miss some genuinely full-width content.

### Solution 3: Context-Aware Assignment

Use vertical gap analysis to group related content:

```python
def assign_column_ids_context_aware(fragments, page_width, col_starts):
    """
    Assign ColId considering vertical gaps between fragments.
    
    If fragments are part of a continuous flow (small vertical gaps),
    assign them the same ColId even if widths vary.
    """
    # Group fragments by vertical proximity
    groups = group_by_vertical_gap(fragments, typical_line_height)
    
    for group in groups:
        # Determine dominant ColId for the group
        widths = [f["width"] for f in group]
        avg_width = sum(widths) / len(widths)
        
        # Assign same ColId to entire group
        if avg_width >= page_width * 0.50:
            for f in group:
                f["col_id"] = 0
        else:
            for f in group:
                f["col_id"] = 1
```

### Solution 4: Post-Processing Smoothing

After initial assignment, smooth out isolated transitions:

```python
def smooth_colid_transitions(fragments, min_group_size=3):
    """
    Smooth out isolated ColId transitions.
    
    If a small group (<min_group_size) of fragments has a different ColId
    than its neighbors, reassign to match neighbors.
    """
    # Sort by reading order
    fragments.sort(key=lambda f: f["reading_order_index"])
    
    # Find isolated groups
    i = 0
    while i < len(fragments):
        current_col_id = fragments[i]["col_id"]
        group_start = i
        
        # Find end of current ColId group
        while i < len(fragments) and fragments[i]["col_id"] == current_col_id:
            i += 1
        
        group_size = i - group_start
        
        # If group is small and surrounded by different ColId, reassign
        if group_size < min_group_size:
            # Check prev and next
            prev_col_id = fragments[group_start - 1]["col_id"] if group_start > 0 else None
            next_col_id = fragments[i]["col_id"] if i < len(fragments) else None
            
            if prev_col_id == next_col_id and prev_col_id != current_col_id:
                # Reassign isolated group to match neighbors
                for j in range(group_start, i):
                    fragments[j]["col_id"] = prev_col_id
```

## Recommended Fix

**Combination approach** for best results:

1. **Detect single-column pages** (Solution 1)
2. **Apply smoothing** (Solution 4) to reduce weaving on multi-column pages
3. **Adjust threshold** (Solution 2) as needed for specific document types

### Implementation Priority

1. **HIGH PRIORITY**: Solution 1 (single-column detection)
   - Fixes the most common case
   - Minimal risk of breaking multi-column detection
   
2. **MEDIUM PRIORITY**: Solution 4 (post-processing smoothing)
   - Cleans up edge cases
   - Works well with Solution 1
   
3. **LOW PRIORITY**: Solutions 2 & 3
   - Fine-tuning for specific document types
   - May require experimentation

## Testing Strategy

1. **Test on single-column pages** with varied content:
   - Short headers
   - Full-width paragraphs
   - Indented paragraphs
   - Section headers
   
2. **Test on multi-column pages** to ensure no regression:
   - Two-column layouts
   - Three-column layouts
   - Mixed single/multi-column pages
   
3. **Verify reading order**:
   - Check ReadingOrderBlock assignments
   - Verify no fragmentation of continuous content
   - Test XML generation and paragraph detection

## Next Steps

1. Run `analyze_colid_weaving.py` on your document
2. Identify pages with weaving issues
3. Choose solution approach based on document characteristics
4. Implement fix in `pdf_to_excel_columns.py`
5. Re-test and verify improvements
