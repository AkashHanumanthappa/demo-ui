#!/usr/bin/env python3
"""
Analyze why superscript fragments don't merge

Example case:
<text top="191" left="101" width="428" height="18" font="11">detail shortly, MRI uses radio waves with frequencies around 10</text>
<text top="192" left="529" width="5" height="11" font="20">7</text>

Expected: Should merge into "...around 10^7" or "...around 10⁷"
Actual: Likely treated as separate rows/fragments
"""

# Fragment 1: Main text ending with "10"
frag1 = {
    "top": 191,
    "left": 101,
    "width": 428,
    "height": 18,
    "text": "detail shortly, MRI uses radio waves with frequencies around 10",
    "font": "11"
}

# Fragment 2: Superscript "7"
frag2 = {
    "top": 192,
    "left": 529,
    "width": 5,
    "height": 11,
    "text": "7",
    "font": "20"
}

print("="*80)
print("SUPERSCRIPT MERGE ANALYSIS")
print("="*80)

# Step 1: Calculate baselines
frag1["baseline"] = frag1["top"] + frag1["height"]
frag2["baseline"] = frag2["top"] + frag2["height"]

print("\nStep 1: Calculate Baselines")
print(f"Fragment 1: baseline = top + height = {frag1['top']} + {frag1['height']} = {frag1['baseline']}")
print(f"Fragment 2: baseline = top + height = {frag2['top']} + {frag2['height']} = {frag2['baseline']}")
print(f"Baseline difference: |{frag1['baseline']} - {frag2['baseline']}| = {abs(frag1['baseline'] - frag2['baseline'])} pixels")

# Step 2: Baseline tolerance
print("\nStep 2: Baseline Tolerance Check")
print(f"Typical baseline tolerance: ~2.0 pixels (computed from median line spacing)")
print(f"Baseline difference: {abs(frag1['baseline'] - frag2['baseline'])} pixels")
if abs(frag1['baseline'] - frag2['baseline']) > 2.0:
    print(f"❌ FAIL: Baseline difference ({abs(frag1['baseline'] - frag2['baseline'])}px) > tolerance (2.0px)")
    print(f"   Result: Fragments will be in DIFFERENT ROWS")
else:
    print(f"✓ PASS: Baseline difference within tolerance")
    print(f"   Result: Fragments will be in SAME ROW")

# Step 3: If they were in same row, would they merge?
print("\nStep 3: IF They Were in Same Row - Merge Check")
frag1_right = frag1["left"] + frag1["width"]
frag2_left = frag2["left"]
gap = frag2_left - frag1_right

print(f"Fragment 1 right edge: left + width = {frag1['left']} + {frag1['width']} = {frag1_right}")
print(f"Fragment 2 left edge: {frag2_left}")
print(f"Horizontal gap: {frag2_left} - {frag1_right} = {gap} pixels")

print("\nMerge logic check (from merge_inline_fragments_in_row):")
gap_tolerance = 1.5  # Default from code

# Phase 1: Trailing space check
frag1_ends_with_space = frag1["text"].endswith(" ")
frag2_starts_with_space = frag2["text"].startswith(" ")
print(f"\nPhase 1: Trailing space detection")
print(f"  Fragment 1 ends with space? {frag1_ends_with_space}")
print(f"  Fragment 2 starts with space? {frag2_starts_with_space}")
if frag1_ends_with_space and not frag2_starts_with_space:
    if abs(gap) <= gap_tolerance:
        print(f"  ✓ Would merge (trailing space + gap ~0)")
    else:
        print(f"  ✗ Would NOT merge (gap too large)")
else:
    print(f"  ✗ Phase 1 criteria not met")

# Phase 2: No-gap merge
print(f"\nPhase 2: Inline-style / no-gap merge")
print(f"  Gap: {gap} pixels")
print(f"  Tolerance: {gap_tolerance} pixels")
if abs(gap) <= gap_tolerance:
    print(f"  ✓ Would merge (|gap| <= tolerance)")
else:
    print(f"  ✗ Would NOT merge (|gap| > tolerance)")

# Phase 3: Space-start continuation
print(f"\nPhase 3: Space-start continuation")
if frag2_starts_with_space:
    space_width = 1.0
    if abs(gap - space_width) <= gap_tolerance:
        print(f"  ✓ Would merge (gap matches space width)")
    else:
        print(f"  ✗ Would NOT merge (gap doesn't match space width)")
else:
    print(f"  ✗ Phase 3 criteria not met (no leading space)")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

baseline_diff = abs(frag1['baseline'] - frag2['baseline'])
in_same_row = baseline_diff <= 2.0
would_merge_if_same_row = abs(gap) <= gap_tolerance

print(f"\n1. Are they in the same row?")
print(f"   Baseline difference: {baseline_diff} pixels")
print(f"   Tolerance: ~2.0 pixels")
if in_same_row:
    print(f"   ✓ YES - Same row")
else:
    print(f"   ❌ NO - Different rows")

if in_same_row:
    print(f"\n2. Would they merge in the same row?")
    print(f"   Gap: {gap} pixels")
    print(f"   Tolerance: {gap_tolerance} pixels")
    if would_merge_if_same_row:
        print(f"   ✓ YES - Would merge")
        print(f"\n   FINAL RESULT: ✓ Fragments WOULD merge")
    else:
        print(f"   ❌ NO - Would not merge")
        print(f"\n   FINAL RESULT: ❌ Fragments would NOT merge")
else:
    print(f"\n2. Would they merge?")
    print(f"   N/A - Not in same row, so merge_inline_fragments_in_row() never sees them together")
    print(f"\n   FINAL RESULT: ❌ Fragments will NOT merge (different rows)")

# Root cause
print("\n" + "="*80)
print("ROOT CAUSE")
print("="*80)
print(f"""
The issue is BASELINE MISMATCH due to superscript positioning:

Fragment 1 (normal text):
- Top: {frag1['top']}, Height: {frag1['height']}
- Baseline: {frag1['baseline']}

Fragment 2 (superscript "7"):
- Top: {frag2['top']} (shifted up by 1px)
- Height: {frag2['height']} (smaller font: 11 vs 18)
- Baseline: {frag2['baseline']} (different by {baseline_diff}px)

The baseline difference ({baseline_diff} pixels) exceeds the tolerance (~2.0 pixels),
so they are grouped into DIFFERENT ROWS before the merge logic runs.

Result: "10" and "7" become separate fragments on different rows.
Expected: "10^7" or "10⁷" as one merged fragment.
""")

print("="*80)
print("POTENTIAL SOLUTIONS")
print("="*80)
print("""
1. INCREASE BASELINE TOLERANCE
   - Currently ~2.0 pixels
   - Could increase to ~6-8 pixels to catch superscripts
   - Risk: May incorrectly merge text from different lines
   
2. FONT-AWARE BASELINE ADJUSTMENT
   - Detect small font sizes (< 12pt) near larger text
   - Adjust baseline calculation for subscripts/superscripts
   - Use font size ratio to normalize baselines
   
3. SPECIAL SUPERSCRIPT/SUBSCRIPT DETECTION
   - Check if fragment is very small (width < 10px, height < 12px)
   - Check if adjacent to larger text with small vertical offset
   - Use special merging rules for these cases
   
4. TWO-PASS MERGING
   - First pass: Normal baseline tolerance (2.0px)
   - Second pass: Relaxed tolerance (6.0px) for small fragments only
   - Only merge small fragments in second pass
   
RECOMMENDED: Solution #4 (two-pass merging) or #2 (font-aware baseline)
""")
