# Subscript/Superscript Fix Summary

## Problem

Subscripts and superscripts were appearing as separate `<text>` elements in the generated XML, sometimes with their own `col_id` assignments and incorrect reading order. This caused issues where text like "T₂" would appear as two separate elements:

```xml
<para col_id="1" reading_block="2">
  <text reading_order="3" ...>known as transverse or T</text>
  <text reading_order="4" ...> relaxation. </text>
  <text reading_order="5" ...>2</text>  <!-- Subscript in separate element -->
</para>
```

## Root Cause

The subscript detection threshold `SCRIPT_MAX_HEIGHT = 12` was too strict. Many subscripts are 13px tall, which exceeded the threshold and caused them to not be detected as scripts. This resulted in:

1. Subscripts not being merged with their parent text
2. Subscripts appearing as separate fragments in different reading order
3. Subscripts getting treated as normal text in separate paragraphs

## Solution

**Changed `SCRIPT_MAX_HEIGHT` from 12 to 14 pixels** in `pdf_to_excel_columns.py` (line 20).

This allows the detection of slightly taller subscripts (13-14px) while still avoiding false positives like drop caps (which are typically 30-50px tall).

### Code Change

```python
# Before
SCRIPT_MAX_HEIGHT = 12  # Max height for scripts (drop caps are ~36-48px)

# After  
SCRIPT_MAX_HEIGHT = 14  # Max height for scripts (increased from 12 to catch 13px subscripts)
```

## How It Works

The script detection pipeline (implemented in `pdf_to_excel_columns.py`):

1. **Phase 1: Detection** (line 1569)
   - `detect_and_mark_scripts(fragments)` scans all fragments
   - Uses TOP position (not baseline) to identify subscripts/superscripts
   - Marks fragments with `is_script`, `script_type`, and `script_parent_idx`
   - Very strict criteria to avoid false positives:
     - Width < 15px
     - Height < 14px (was 12px)
     - Text length ≤ 3 characters
     - Adjacent to larger fragment (within 5px)
     - Appropriate vertical offset (using TOP position)

2. **Phase 2: Baseline Grouping** (line 1608)
   - `group_fragments_into_lines(fragments, baseline_tol)` groups by baseline
   - Subscripts end up in different rows due to baseline differences
   - Script markings are preserved through this process

3. **Phase 3: Cross-Row Merging** (line 1613)
   - `merge_scripts_across_rows(raw_rows, fragments)` merges scripts with parents
   - Uses `original_idx` to find parent fragments across rows
   - Creates merged fragments with `original_fragments` tracking
   - Text is marked with `^` for superscripts, `_` for subscripts

4. **Phase 4: Inline Merging** (lines 1615-1617)
   - `merge_inline_fragments_in_row(row)` merges adjacent fragments on same line
   - Preserves `original_fragments` tracking from script merging

5. **XML Generation** (`pdf_to_unified_xml.py`, lines 1437-1461)
   - Checks for `original_fragments` in merged fragments
   - Generates proper inline `<subscript>` and `<superscript>` elements
   - Uses font information from each original fragment

## Expected Result

After the fix, subscripts will be properly merged and appear as inline elements:

```xml
<para col_id="1" reading_block="2">
  <text reading_order="3" ...>
    <phrase font="11">known as transverse or T</phrase>
    <subscript font="12">2</subscript>
    <phrase font="11"> relaxation.</phrase>
  </text>
</para>
```

## Verification

The fix was verified with test case from page 27:

**Fragments:**
- [0] "known as transverse or T" @ left=101, top=171, height=18px
- [2] "2" @ left=267, top=179, height=13px  ← **13px tall**
- [1] " relaxation. " @ left=273, top=171, height=18px

**Test Results:**
```
✓ Fragment [2] '2' detected as subscript of [0] 'known as transverse or T'
```

The subscript "2" (13px) now passes the size check and is correctly identified as a subscript of "T".

## Impact

This fix will improve the handling of:
- Scientific notation (10⁷, 10⁻³)
- Chemical formulas (H₂O, CO₂)
- Mathematical subscripts/superscripts (x₁, aⁿ)
- Reference markers ([1], [2])

## Safety

The threshold increase is conservative:
- **Old threshold:** 12px (too strict, missed 13px subscripts)
- **New threshold:** 14px (catches 13-14px subscripts)
- **Drop caps:** 30-50px (still well above threshold)
- **False positive margin:** 16px+ buffer for safety

## Files Modified

1. `pdf_to_excel_columns.py` (line 20)
   - Changed `SCRIPT_MAX_HEIGHT` from 12 to 14

## Testing

Two test files were created to verify the fix:

1. `debug_subscript_issue.py` - Analyzes the specific issue case
2. `test_subscript_fix_simple.py` - Tests detection logic with the fix

Both tests confirm the subscript is now correctly detected.

## Recommendation

Process the PDF again with this fix to regenerate the XML with properly merged subscripts/superscripts.

## Future Improvements

If needed, the threshold could be made adaptive based on the median font size on each page, but the fixed threshold of 14px should work well for most documents.
