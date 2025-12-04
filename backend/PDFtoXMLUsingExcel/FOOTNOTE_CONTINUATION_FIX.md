# Footnote Zone Continuation Line Fix

## Problem

When processing reference pages or bibliography sections, narrow continuation lines at the bottom of the page were being incorrectly assigned different `col_id` values than their parent entries, causing broken reading order.

### Example Issue (Page 1010)

```
Reference 19: col_id=1 (above footnote zone) ✓
Reference 20 (line 1): col_id=0 (wide, 594px) ✓
Reference 20 (line 2): col_id=0 (wide, 571px) ✓
Reference 20 (line 3): col_id=1 (narrow, 120px) ✗ WRONG!
Reference 21 (line 1): col_id=0 (wide, 598px) ✓
...
```

This created incorrect reading order:
1. References 6-19
2. **"Accessed June, 2020." (line 3 of ref 20)** ← Read too early!
3. **Reference 20 (lines 1-2)** ← Read too late!
4. References 21-22

## Root Cause

The `reclassify_footnote_rows_as_fullwidth()` function correctly identified wide reference entries in the footnote zone (bottom 25% of page) and assigned them `col_id=0`. However, narrow continuation lines failed the width threshold check (60% of page width) and kept `col_id=1`.

The existing `group_col0_by_vertical_gap()` function was designed to propagate `col_id=0` to nearby fragments, but it required fragments to be ≥40% of page width. Narrow continuation lines like "Accessed June, 2020." (120px = 14% of 823px page) didn't meet this threshold.

## Solution

Modified `group_col0_by_vertical_gap()` to add special handling for the **footnote zone** (bottom 25% of page):

```python
# Footnote zone threshold (bottom 25% of page)
footnote_threshold = page_height * 0.75 if page_height else float('inf')

# Check if current fragment is in footnote zone
in_footnote_zone = current.get("top", 0) >= footnote_threshold

# In footnote zone: propagate ColID 0 to continuation lines regardless of width
# Outside footnote zone: only propagate if fragment is wide enough
if in_footnote_zone or next_width >= min_width_for_col0:
    next_frag["col_id"] = 0
```

## How It Works

1. **Detect footnote zone**: Any fragment with `top >= page_height * 0.75` is in the footnote zone
2. **Track parent-child relationships**: When a `col_id=0` fragment is found in the footnote zone
3. **Propagate to children**: Nearby fragments (vertical gap ≤ 1.5× line height) inherit `col_id=0` **regardless of width**
4. **Preserve non-footnote content**: Fragments above the footnote zone follow the normal width-based rules

## Impact

### Before Fix
- Narrow continuation lines got `col_id=1`
- Reading order was broken (interleaved col_id=0 and col_id=1)
- References were split across different reading blocks

### After Fix
- All lines of a reference entry get the same `col_id=0`
- Reading order flows correctly top-to-bottom
- References are grouped together in `reading_block=2`

## Testing

Run the test to verify the fix:

```bash
python3 test_footnote_continuation_fix.py
```

Expected output:
```
✅ PASS: Narrow fragment at top=939 (width=120) correctly has col_id=0
✅ PASS: Narrow fragment at top=1033 (width=314) correctly has col_id=0
✅ PASS: All 8 fragments in footnote zone have col_id=0
✅ PASS: Fragment above footnote zone (top=851) correctly kept col_id=1
```

## Code Changes

**File**: `pdf_to_excel_columns.py`

**Function Modified**: `group_col0_by_vertical_gap()`
- Added `page_height` parameter
- Added footnote zone detection logic
- Modified propagation logic to skip width check in footnote zone

**Call Site Updated**: Line 1065
- Now passes `page_height=page_height` parameter

## Edge Cases Handled

1. **Hanging indents**: Continuation lines starting at left=155 (indented from left=128)
2. **Variable widths**: Lines ranging from 120px to 598px all grouped together
3. **Multiple references**: Logic works across multiple reference entries
4. **Boundary conditions**: Only applies to bottom 25% of page, not entire page

## Why Bottom 25%?

The 25% threshold (`page_height * 0.75`) is based on typical page layouts:
- Main content: Top 75% of page
- Footnotes/references at bottom: Bottom 25% of page
- This matches the existing `reclassify_footnote_rows_as_fullwidth()` threshold

This prevents incorrectly grouping legitimate column content higher up on the page.
