# Subscript/Superscript Fix - Quick Guide

## The Problem

Subscripts like "T₂" were appearing as separate text elements with wrong reading order:

```xml
<!-- BEFORE (BROKEN) -->
<para col_id="1" reading_block="2">
  <text reading_order="3">transverse or T</text>
  <text reading_order="4"> relaxation. </text>
  <text reading_order="5">2</text>  <!-- Subscript separate! -->
</para>
```

## The Fix

**One line change in `pdf_to_excel_columns.py` line 20:**

```python
SCRIPT_MAX_HEIGHT = 14  # Was 12, increased to catch 13px subscripts
```

## Expected Output

```xml
<!-- AFTER (FIXED) -->
<para col_id="1" reading_block="2">
  <text reading_order="3">
    <phrase font="11">transverse or T</phrase>
    <subscript font="12">2</subscript>
    <phrase font="11"> relaxation.</phrase>
  </text>
</para>
```

## What Happens Now

1. **Detection:** Subscripts up to 14px tall are now detected (was 12px)
2. **Merging:** Subscripts are merged with their parent text inline
3. **Tracking:** Original fragments are tracked for proper XML output
4. **XML:** Generates proper `<subscript>` and `<superscript>` elements

## To Apply

Re-process your PDF:

```bash
python pdf_to_unified_xml.py your_document.pdf --full-pipeline
```

The subscripts will now be properly merged and formatted.

## What It Fixes

- Scientific notation: 10⁷, 10⁻³
- Chemical formulas: H₂O, CO₂
- Math subscripts: x₁, x₂
- Reference markers: proper inline positioning

## Technical Details

See `SUBSCRIPT_FIX_SUMMARY.md` for complete technical documentation.
