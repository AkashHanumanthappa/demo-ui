# ReadingOrderBlock Numbering Issue - Analysis

## Problem Description

The ReadingOrderBlock numbering is not incrementing correctly. The observed behavior is:
1. ReadingOrderBlock = 1 (initial content)
2. Column assignments happen (col_id assignments)
3. ReadingOrderBlock = 2 with ColID = 0
4. **ReadingOrderBlock goes back to 1** (INCORRECT - should continue incrementing)

## Root Cause Analysis

### Current Logic in `assign_reading_order_blocks()` (lines 459-527)

The function assigns reading order blocks based on this logic:

```python
Block 1: Full-width content ABOVE columns (col_id=0 and baseline < first_col_min_baseline)
Block 2: Column 1 (all fragments with col_id=1)
Block 3: Column 2 (all fragments with col_id=2)
Block 4: Column 3... (if exists)
Block N: Full-width content BELOW/WITHIN columns (col_id=0 and baseline >= first_col_min_baseline)
```

### The Problem

The current logic treats **ALL** `col_id=0` fragments that appear at or below the column start baseline as belonging to a **SINGLE** block (the final block). This is incorrect when:

1. **Full-width content appears BETWEEN columns vertically**
   - Example: A figure caption or heading that spans full width appears between column 1 and column 2
   
2. **Multiple full-width sections exist at different vertical positions**
   - Example: 
     - Full-width heading at top
     - Column 1 content
     - Full-width figure/table in middle
     - Column 2 content
     - Full-width footnote at bottom

### Specific Code Issue

**Lines 519-526:**
```python
# Final block: Full-width content BELOW/WITHIN columns
below_fullwidth = [
    f for f in fragments
    if f["col_id"] == 0 and f["baseline"] >= first_col_min_baseline
]
if below_fullwidth:
    for f in below_fullwidth:
        f["reading_order_block"] = block_num  # ALL get same block_num!
```

**The bug:** All col_id=0 fragments below the first column start get assigned to the **same** block number, regardless of their vertical position. This means:
- Full-width content that should come AFTER column 1 but BEFORE column 2 gets lumped into the same block as content that comes AFTER column 2
- The reading order becomes non-sequential

## Example Scenario

### Page Layout:
```
Page Structure:
+------------------------------------------+
| ReadingOrderBlock 1: Title (col_id=0)   | baseline: 100
+------------------------------------------+
| ReadingOrderBlock 2: Column 1 (col_id=1)| baseline: 120-300
+------------------+-----------------------+
| ReadingOrderBlock 3: Figure (col_id=0)   | baseline: 320
+------------------------------------------+
| ReadingOrderBlock 4: Column 2 (col_id=2)| baseline: 340-500
+------------------+-----------------------+
| ReadingOrderBlock 5: Footnote (col_id=0) | baseline: 520
+------------------------------------------+
```

### Current (Incorrect) Behavior:
- Block 1: Title (col_id=0, baseline < 120) ✓ CORRECT
- Block 2: All of Column 1 (col_id=1) ✓ CORRECT
- Block 3: All of Column 2 (col_id=2) ✓ CORRECT
- Block 4: **BOTH Figure AND Footnote** (both col_id=0, baseline >= 120) ❌ WRONG!

Result: Figure and Footnote are in the same block, even though Figure should come before Column 2, and Footnote should come after.

### Expected (Correct) Behavior:
The reading order should be based on **vertical position (baseline)**, not just col_id:

1. Block 1: Title (col_id=0, baseline < first column)
2. Block 2: Column 1 content up to baseline 300 (col_id=1)
3. Block 3: Figure (col_id=0, baseline 320 - between columns vertically)
4. Block 4: Column 2 content from baseline 340 (col_id=2)
5. Block 5: Footnote (col_id=0, baseline 520 - after all columns)

## Proposed Solution

### Option 1: Interleaved Block Assignment (Recommended)

Instead of grouping all col_id=0 fragments together, we should **interleave** them based on baseline position:

1. Sort all fragments by baseline
2. Group consecutive fragments with the same col_id
3. Assign block numbers sequentially to each group

Example algorithm:
```python
# Sort all fragments by baseline
sorted_fragments = sorted(fragments, key=lambda f: f["baseline"])

# Group consecutive fragments by col_id
current_col = None
current_block = 1
for frag in sorted_fragments:
    if frag["col_id"] != current_col:
        # New column/block
        current_col = frag["col_id"]
        current_block += 1
    frag["reading_order_block"] = current_block
```

This would naturally handle:
- Full-width content above columns
- Column 1
- Full-width content between columns
- Column 2
- Full-width content below columns

### Option 2: Three-Phase Assignment

More complex but handles special cases:

1. **Phase 1:** Assign block to full-width content ABOVE columns (baseline < first_col_min_baseline)
2. **Phase 2:** Interleave columns and full-width content WITHIN column region (baseline >= first_col_min_baseline and baseline <= last_col_max_baseline)
3. **Phase 3:** Assign block to full-width content BELOW columns (baseline > last_col_max_baseline)

## Impact Analysis

### Files Affected:
- `pdf_to_excel_columns.py` - Function `assign_reading_order_blocks()` (lines 459-527)

### Dependencies:
- Called after `assign_reading_order_from_rows()` (line 1512)
- Affects Excel output columns: ReadingOrderBlock, ColID (lines 1525-1540)
- Affects XML output in `pdf_to_unified_xml.py` (line 881): sorting uses `reading_order_block`

### Tests Needed:
- Test case with full-width content between two columns
- Test case with multiple full-width sections at different vertical positions
- Test case with standard two-column layout (no full-width content in middle)

## Recommendation

Implement **Option 1** (Interleaved Block Assignment) because:
1. Simpler logic - easier to maintain
2. Naturally handles all cases based on vertical position
3. Aligns with the natural reading order of the document
4. More robust for complex layouts

The current logic assumes a simple structure (full-width above → columns → full-width below), but real documents have more complex layouts with interleaved content.
