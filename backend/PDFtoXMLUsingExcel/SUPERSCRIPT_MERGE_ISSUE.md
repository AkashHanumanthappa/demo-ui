# Superscript/Subscript Merge Issue - Deep Analysis

## The Real Problem You Discovered

Your ColId weaving issue may be a **symptom** of a deeper problem: **inline fragments (especially superscripts/subscripts) are not being merged properly**.

---

## Example Case Analysis

### Your Example
```xml
<text top="191" left="101" width="428" height="18" font="11">detail shortly, MRI uses radio waves with frequencies around 10</text>
<text top="192" left="529" width="5" height="11" font="20">7</text>
```

**Expected**: "...around 10⁷" (merged as one fragment)  
**Actual**: "...around 10" and "7" (separate fragments on different rows)

---

## Root Cause: Baseline Mismatch

### Current Baseline Calculation
```python
baseline = top + height
```

**Fragment 1** (normal text "...10"):
- Top: 191, Height: 18
- **Baseline: 209**

**Fragment 2** (superscript "7"):
- Top: 192, Height: 11 (smaller font)
- **Baseline: 203**

**Baseline difference**: 6 pixels

### Why It Doesn't Merge

**Step 1**: `group_fragments_into_lines()` uses baseline tolerance (~2.0 pixels)
```python
baseline_tol = compute_baseline_tolerance(baselines)  # Returns ~2.0
```

**Step 2**: Fragments with baseline difference > 2.0px → **different rows**
```python
if abs(b - current_baseline) <= baseline_tol:  # 6 > 2.0 → FALSE
    current.append(f)  # Not added to same row
else:
    lines.append(current)  # Start new row
```

**Step 3**: `merge_inline_fragments_in_row()` only runs within each row
- Fragment 1 is in Row 1
- Fragment 2 is in Row 2  
- They **never get to the merge logic**

---

## Why This Matters for ColId

When superscripts/subscripts don't merge:

1. **Fragment 1**: "...frequencies around 10"
   - Width: 428px (likely < 45% of page width)
   - → **ColId 1**

2. **Fragment 2**: "7"
   - Width: 5px (definitely < 45% of page width)
   - → **ColId 1**

But they're on **different rows** (row_index differs), so:
- They may get different ReadingOrderBlock assignments
- They may trigger transitions if surrounding content has ColId 0
- The "7" fragment may be misclassified or skipped entirely

**Even worse**: If the merged fragment would be wide enough, it should be ColId 0, but since it's split, both parts get ColId 1.

---

## Impact Analysis

### How Common Is This?

Superscripts/subscripts appear in:
- **Scientific notation**: 10⁷, 10⁻³, CO₂, H₂O
- **References**: citation numbers [1], footnote markers ¹
- **Ordinals**: 1st, 2nd, 3rd
- **Mathematical formulas**: x², y³, aⁿ

### Consequences

1. **Broken text flow**: "10" and "7" are separate, meaning:
   - Search/indexing breaks: Can't find "10⁷"
   - Copy/paste breaks: User gets "10" on one line, "7" on another
   - Screen readers break: "ten... seven" instead of "ten to the seventh"

2. **Reading order disruption**: 
   - Superscript on separate row → separate reading_order_index
   - May appear in wrong position in final XML

3. **ColId assignment issues**:
   - Fragment widths incorrect (split instead of merged)
   - May trigger ColId transitions
   - May affect full-width detection

4. **Paragraph detection issues**:
   - Row index changes → paragraph break
   - "...10" becomes end of paragraph, "7" starts new paragraph

---

## Current Merge Logic Review

### The Merge Function
```python
def merge_inline_fragments_in_row(row, gap_tolerance=1.5, space_width=1.0):
```

**Phases**:
1. **Trailing space**: If previous ends with space and gap ~0 → merge
2. **No-gap**: If |gap| ≤ 1.5px → merge
3. **Space-start**: If next starts with space and gap ~1.0px → merge

**For your example**:
- Gap = 0 pixels (fragment 1 ends at 529, fragment 2 starts at 529)
- **Phase 2 would merge them** (0 ≤ 1.5) ✓

**But**: They never reach this function because they're in different rows!

---

## Solution Approaches

### Option 1: Increase Baseline Tolerance ⚠️

**Change**:
```python
def compute_baseline_tolerance(baselines):
    # OLD:
    tol = min(2.0, line_spacing * 0.4)
    
    # NEW:
    tol = min(6.0, line_spacing * 0.4)  # Increased from 2.0 to 6.0
```

**Pros**:
- Simple one-line change
- Catches most superscripts/subscripts

**Cons**:
- May incorrectly merge text from different lines
- Could merge lines that are actually 4-5px apart
- Not targeted to the actual problem

**Risk**: HIGH - Could break normal text flow

---

### Option 2: Font-Aware Baseline Normalization ✓

**Concept**: Normalize baselines based on font size

```python
def normalize_baseline(fragment, reference_height):
    """
    Adjust baseline for superscripts/subscripts.
    
    If fragment has smaller font, adjust its baseline to match
    the expected baseline of the reference font size.
    """
    if fragment["height"] < reference_height * 0.75:
        # This is likely a super/subscript (< 75% of normal height)
        # Normalize to reference baseline
        height_ratio = fragment["height"] / reference_height
        # Adjust top to align baselines
        adjusted_baseline = fragment["top"] + reference_height
        return adjusted_baseline
    else:
        # Normal text
        return fragment["baseline"]
```

**Apply before grouping**:
```python
# Calculate median height (reference)
heights = [f["height"] for f in fragments]
reference_height = statistics.median(heights)

# Normalize baselines for comparison
for f in fragments:
    f["normalized_baseline"] = normalize_baseline(f, reference_height)

# Group by normalized baseline
rows = group_fragments_into_lines(fragments, baseline_tol, use_normalized=True)
```

**Pros**:
- Targeted to actual problem (font size differences)
- Won't affect normal text
- Preserves original baseline for downstream use

**Cons**:
- More complex
- Requires testing on various document types

**Risk**: MEDIUM - Requires careful implementation

---

### Option 3: Special Superscript/Subscript Detection ✓✓

**Concept**: Detect and handle super/subscripts explicitly

```python
def detect_superscript_subscript(fragments):
    """
    Detect fragments that are likely superscripts or subscripts.
    
    Criteria:
    - Small width (< 20px)
    - Small height (< 12px or < 75% of nearby text)
    - Adjacent to larger text (left/right within 5px)
    - Vertical offset from baseline (±3-8px)
    """
    for i, f in enumerate(fragments):
        # Check size
        if f["width"] > 20 or f["height"] > 12:
            continue
        
        # Check if adjacent to larger text
        prev_frag = fragments[i-1] if i > 0 else None
        next_frag = fragments[i+1] if i < len(fragments) - 1 else None
        
        is_adjacent = False
        if prev_frag:
            gap = f["left"] - (prev_frag["left"] + prev_frag["width"])
            if abs(gap) < 5 and prev_frag["height"] > f["height"]:
                is_adjacent = True
                f["superscript_of"] = i - 1
        
        if next_frag and not is_adjacent:
            gap = next_frag["left"] - (f["left"] + f["width"])
            if abs(gap) < 5 and next_frag["height"] > f["height"]:
                is_adjacent = True
                f["subscript_of"] = i + 1
        
        if is_adjacent:
            f["is_script"] = True
```

**Then merge explicitly**:
```python
def merge_superscripts_subscripts(fragments):
    """Merge detected superscripts/subscripts with their base text."""
    merged = []
    skip = set()
    
    for i, f in enumerate(fragments):
        if i in skip:
            continue
        
        # Check if next fragment is a superscript of this one
        if i + 1 < len(fragments):
            next_f = fragments[i + 1]
            if next_f.get("superscript_of") == i:
                # Merge
                merged_text = f["text"] + "^" + next_f["text"]
                # Or use Unicode: merged_text = f["text"] + superscript(next_f["text"])
                f["text"] = merged_text
                f["width"] = f["width"] + next_f["width"]
                skip.add(i + 1)
        
        merged.append(f)
    
    return merged
```

**Pros**:
- Explicit and clear
- Can add special formatting (^ or Unicode superscripts)
- Preserves document structure
- Easy to test and debug

**Cons**:
- Most complex implementation
- Requires careful detection logic

**Risk**: LOW - Explicit handling, easy to disable

---

### Option 4: Two-Pass Merging ✓✓ (RECOMMENDED)

**Concept**: Two passes with different tolerances

```python
def group_fragments_with_superscripts(fragments, baseline_tol):
    """
    Two-pass grouping:
    1. Normal pass: Group by strict baseline tolerance
    2. Superscript pass: Merge small fragments with relaxed tolerance
    """
    # Pass 1: Normal grouping
    rows = group_fragments_into_lines(fragments, baseline_tol)
    
    # Pass 2: Find small fragments (potential super/subscripts)
    all_fragments = [f for row in rows for f in row]
    
    for i, f in enumerate(all_fragments):
        # Is this a small fragment?
        if f["width"] < 20 and f["height"] < 12:
            # Look for adjacent larger fragment within relaxed tolerance
            for j, other in enumerate(all_fragments):
                if i == j:
                    continue
                
                # Check if adjacent horizontally
                horizontal_gap = abs(f["left"] - (other["left"] + other["width"]))
                if horizontal_gap > 5:
                    continue
                
                # Check if within relaxed baseline tolerance
                baseline_gap = abs(f["baseline"] - other["baseline"])
                if baseline_gap <= 8:  # Relaxed: 8px instead of 2px
                    # Found a match - merge them
                    # (Implementation details...)
                    pass
    
    return rows
```

**Pros**:
- Preserves normal text flow
- Only affects small fragments
- Relatively simple
- Low risk of breaking existing behavior

**Cons**:
- Two passes (minimal performance impact)
- May miss some edge cases

**Risk**: LOW - Conservative, targeted approach

---

## Recommended Solution

**Use Option 4 (Two-Pass Merging)** with enhancements from Option 3 (Detection):

### Phase 1: Detect Scripts
```python
def detect_scripts(fragments):
    """Mark fragments as super/subscripts."""
    for i, f in enumerate(fragments):
        if f["width"] < 20 and f["height"] < 12:
            # Check adjacency to larger text
            f["is_potential_script"] = check_adjacent_larger_text(f, fragments)
```

### Phase 2: Two-Pass Grouping
```python
def group_fragments_into_lines_v2(fragments, baseline_tol):
    # Pass 1: Normal grouping
    rows = group_fragments_into_lines(fragments, baseline_tol)
    
    # Pass 2: Merge scripts with relaxed tolerance
    rows = merge_adjacent_scripts(rows, relaxed_tol=8.0)
    
    return rows
```

### Phase 3: Inline Merge
```python
# Existing merge_inline_fragments_in_row() handles the rest
```

---

## Implementation Plan

### Step 1: Add Script Detection
Add before line 1139 in `pdf_to_excel_columns.py`:

```python
def detect_potential_scripts(fragments):
    """Detect fragments that might be superscripts/subscripts."""
    for i, f in enumerate(fragments):
        f["is_potential_script"] = (
            f["width"] < 20 and 
            f["height"] < 12 and
            len(f["text"]) <= 3
        )
```

### Step 2: Modify Baseline Grouping
Replace `group_fragments_into_lines()` with two-pass version:

```python
def group_fragments_into_lines_with_scripts(fragments, baseline_tol):
    # Pass 1: Normal grouping with standard tolerance
    rows = []
    # ... existing logic ...
    
    # Pass 2: Try to merge potential scripts with adjacent rows
    for potential_script in fragments:
        if not potential_script.get("is_potential_script"):
            continue
        
        # Try to find parent row within relaxed tolerance
        # ... merging logic ...
    
    return rows
```

### Step 3: Test
Test on documents with:
- Scientific notation (10⁷)
- Chemical formulas (H₂O)
- Reference numbers ([1], ¹)
- Ordinals (1st, 2nd)

---

## Testing Strategy

### Test Cases

1. **Scientific notation**:
   ```xml
   <text>10</text><text font-size="smaller">7</text>
   ```
   Expected: "10⁷" or "10^7"

2. **Chemical formulas**:
   ```xml
   <text>H</text><text font-size="smaller">2</text><text>O</text>
   ```
   Expected: "H₂O" or "H2O"

3. **Reference markers**:
   ```xml
   <text>some text</text><text font-size="smaller">1</text>
   ```
   Expected: "some text¹" or "some text[1]"

4. **Normal text** (should not be affected):
   ```xml
   <text top="100">Line 1</text>
   <text top="120">Line 2</text>
   ```
   Expected: Separate lines (not merged)

---

## Impact on ColId Weaving

### Before Fix:
```
Fragment: "...around 10"      width=428px  → ColId calculation
Fragment: "7"                 width=5px    → ColId calculation
Both treated separately → potential ColId transitions
```

### After Fix:
```
Fragment: "...around 10^7"    width=433px  → Single ColId calculation
One merged fragment → no artificial transitions
```

**Result**: Fewer false ColId transitions, more stable ReadingOrderBlock assignments.

---

## Next Steps

1. **Analyze your actual XML** to see how common this is
2. **Implement Option 4** (two-pass merging) as the safest approach
3. **Test on sample pages** with known superscripts/subscripts
4. **Monitor impact** on ColId assignments and reading order

This may solve more of your ColId weaving issues than the single-column detection alone!

---

## Tools Created

- `analyze_superscript_merge.py` - Analyzes why specific fragments don't merge
- Run on your XML fragments to diagnose merge issues

**Usage**:
```bash
python3 analyze_superscript_merge.py
```

Modify the script to test your specific fragment pairs from the XML.
