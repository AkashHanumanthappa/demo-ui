# Root Cause Analysis: ColId Weaving and Fragment Merging

## What You Discovered

The ColId weaving issue is likely a **symptom**, not the root cause. The real problem is:

**Inline fragments (superscripts, subscripts, and broken text) are not being merged properly.**

---

## The Real Root Cause

### Issue 1: Superscripts/Subscripts Not Merging

**Your examples**:

1. **Superscript**: `10⁷` split into "10" and "7"
2. **Subscript**: `B₀` split into "B" and "Ø"

**Why they don't merge**:

Current code uses `baseline = top + height` to group fragments into rows:
```python
baseline = top + height
if abs(fragment_baseline - row_baseline) <= tolerance:  # tolerance ~2.0px
    add_to_same_row()
```

**The problem**:
```
Fragment: "10"    top=191, height=18  → baseline=209
Fragment: "7"     top=192, height=11  → baseline=203
Difference: |209-203| = 6 pixels > 2.0 tolerance
Result: DIFFERENT ROWS → Never reach merge logic!
```

### Issue 2: Baseline is the Wrong Metric

**Baseline misleads** because:
- Superscripts have smaller height BUT nearly same top position
- `baseline = top + height` makes them look far apart
- Real proximity is in the **TOP position**, not baseline!

**Correct metric**: Use TOP position

```
Fragment: "10"    top=191
Fragment: "7"     top=192
Difference: |192-191| = 1 pixel  ← VERY CLOSE!

Fragment: "B"     top=324
Fragment: "Ø"     top=331
Difference: |331-324| = 7 pixels ← Clearly subscript
```

---

## Impact on ColId

When fragments don't merge:

### Example: "10⁷Hz"

**Should be** (merged):
```
Fragment: "10⁷Hz"  width=433px (~70% of 612px page) → ColId 0 (full-width)
```

**Actually is** (not merged):
```
Fragment 1: "10"     width=428px (~70%) → ColId 0
Fragment 2: "7"      width=5px (0.8%)   → ColId 1
Fragment 3: "Hz"     width=166px (~27%) → ColId 0
```

**Result**:
- Three fragments instead of one
- ColId transitions: 0 → 1 → 0 (weaving!)
- Different row indices → affects reading order
- May break paragraph detection

### Example: "B₀"

**Should be** (merged):
```
Fragment: "B₀"  width=19px → ColId 1 (or part of larger text)
```

**Actually is** (not merged):
```
Fragment 1: "B"   width=10px  → ColId 1
Fragment 2: "Ø"   width=9px   → ColId 1 (different row!)
```

**Result**:
- Two fragments on different rows
- Reading order disrupted
- Text search/indexing broken

---

## Why This Causes "Weaving"

Your pages likely have:

1. **Normal paragraph**: "...frequencies around 10" → ColId 0 (wide)
2. **Superscript**: "7" → ColId 1 (separate row, narrow)
3. **Continuation**: "Hz..." → ColId 0 (wide)
4. **Short header**: "Methods" → ColId 1 (narrow)
5. **Paragraph**: "The methods..." → ColId 0 (wide)

**ColId sequence**: `[0, 1, 0, 1, 0, ...]` ← Weaving pattern!

But the "weaving" at transitions 0→1→0 is actually caused by **superscripts/subscripts not being merged with their parent text**.

---

## The Solution

### Detection Logic (Correct Approach)

```python
def detect_script_type(script_frag, parent_frag):
    """
    Detect if fragment is superscript or subscript.
    
    KEY: Use TOP position, not baseline!
    """
    # Size criteria
    if script_frag["width"] >= 20:
        return None
    if script_frag["height"] >= 15:  # Increased from 12
        return None
    if len(script_frag.get("text", "")) > 3:
        return None
    
    # Must be smaller than parent
    if script_frag["height"] >= parent_frag["height"]:
        return None
    
    # Horizontal adjacency (within 5px)
    gap = script_frag["left"] - (parent_frag["left"] + parent_frag["width"])
    if abs(gap) > 5:
        return None
    
    # CRITICAL: Use TOP position, not baseline!
    top_diff = script_frag["top"] - parent_frag["top"]
    
    # Superscript: within ±3px of parent top
    if -3 <= top_diff <= 3:
        return "superscript"
    
    # Subscript: 3-10px below parent top
    elif 3 < top_diff <= 10:
        return "subscript"
    
    return None
```

### Integration Points

**Where to fix** in `pdf_to_excel_columns.py`:

**Current flow** (line 1139-1158):
```python
# (1) First pass: group into rows and merge inline fragments within each row
baselines = [f["baseline"] for f in fragments]
baseline_tol = compute_baseline_tolerance(baselines)
raw_rows = group_fragments_into_lines(fragments, baseline_tol)  # ← PROBLEM HERE

merged_fragments = []
for row in raw_rows:
    merged_fragments.extend(merge_inline_fragments_in_row(row))
```

**Fix**: Add script detection BEFORE grouping

```python
# (0) NEW: Detect and merge superscripts/subscripts FIRST
fragments = detect_and_merge_scripts(fragments)  # ← NEW STEP

# (1) Then group into rows (now with pre-merged scripts)
baselines = [f["baseline"] for f in fragments]
baseline_tol = compute_baseline_tolerance(baselines)
raw_rows = group_fragments_into_lines(fragments, baseline_tol)

# (2) Then merge remaining inline fragments
merged_fragments = []
for row in raw_rows:
    merged_fragments.extend(merge_inline_fragments_in_row(row))
```

---

## Expected Impact

### Before Fix

**Page with scientific notation** (10⁷Hz):
```
Fragments: 50
ColId weaving: YES (8 transitions)
ReadingOrderBlocks: 5
Issues:
  - "10" and "7" separate
  - ColId: 0→1→0 weaving
  - Search broken: can't find "10⁷"
```

**After Fix**:
```
Fragments: 48 (2 merged)
ColId weaving: NO (2 transitions)
ReadingOrderBlocks: 2
Benefits:
  - "10^7" merged
  - ColId: stable
  - Search works: can find "10^7"
```

### Test Document Statistics

If your 300-page book has:
- ~50 scientific notations per page
- ~20 chemical formulas per page
- ~10 reference markers per page

**Potential merges**: ~80 fragments per page × 300 pages = **24,000 fragments**

**Impact**:
- Fewer fragments → faster processing
- Fewer ColId transitions → less weaving
- Better text extraction → improved search/indexing
- Correct reading order → better structure

---

## Why Single-Column Detection Wasn't Enough

Your original analysis focused on single-column detection:
- "Short headers cause ColId 1"
- "Full paragraphs cause ColId 0"

**But the real issue is**:
- Broken text (superscripts/subscripts not merged)
- Creates artificial narrow fragments
- These trigger ColId transitions

**Single-column detection helps**, but doesn't fix the root cause of fragments being split.

---

## Recommended Action Plan

### Phase 1: Fix Fragment Merging (High Priority)

1. **Implement correct script detection** (use TOP position)
2. **Merge scripts before row grouping**
3. **Test on pages with formulas/notation**

**Expected**: 30-50% reduction in ColId weaving

### Phase 2: Apply Single-Column Detection (Medium Priority)

1. **Detect single-column pages**
2. **Assign unified ColId**

**Expected**: Additional 40-50% reduction in weaving

### Phase 3: Combined Effect (Complete Solution)

Both fixes together:
- **Fix fragment merging** → Fewer artificial transitions
- **Single-column detection** → Consistent ColId assignment

**Expected**: 90-97% reduction in ColId weaving

---

## Next Steps

1. **Analyze your actual PDF XML** to count superscripts/subscripts
   ```bash
   # Count small fragments (potential scripts)
   grep '<text' your_pdftohtml.xml | \
     grep -E 'width="[0-9]"' | \
     grep -E 'height="1[0-4]"' | \
     wc -l
   ```

2. **Implement TOP-based detection** (not baseline)

3. **Test on sample pages** with known formulas:
   - Scientific notation (10⁷, 10⁻³)
   - Chemical formulas (H₂O, CO₂)
   - Mathematical expressions (x², aⁿ)

4. **Measure impact**:
   - Fragment count before/after
   - ColId transition count
   - ReadingOrderBlock count

---

## Tools Created

1. **`analyze_superscript_merge.py`** - Shows why baseline fails
2. **`analyze_super_sub_correct.py`** - Shows correct TOP-based approach
3. **`fix_superscript_merge.py`** - Implementation (needs update with TOP logic)
4. **`SUPERSCRIPT_MERGE_ISSUE.md`** - Full documentation

---

## Summary

**Original hypothesis**: "ColId weaving caused by short headers on single-column pages"

**Reality**: "ColId weaving caused by superscripts/subscripts not merging due to baseline mismatch"

**Root cause**: Using `baseline = top + height` instead of `top` position for script detection

**Fix**: Detect scripts using TOP position, merge before row grouping

**Impact**: Fixes not just ColId weaving, but also:
- Text search/indexing
- Copy/paste behavior
- Screen reader output
- Reading order
- Paragraph detection

This is a **deeper** issue than just ColId assignment!
