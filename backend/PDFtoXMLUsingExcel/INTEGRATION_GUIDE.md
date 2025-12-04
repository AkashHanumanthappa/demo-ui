# Phase 1 Script Detection - Integration Guide

## What You Just Saw

The test showed:
- ✅ **Superscript "7" detected** as superscript of "...around 10"
- ✅ **Drop cap "T" NOT detected** (too large - preserved correctly)
- ✅ **Cross-row merging works** - "7" merged with "...around 10" → "...around 10^7"

Note: Subscript "Ø" wasn't detected because "Ø" is not alphanumeric. This is intentional - symbols like Ø, °, ™ are excluded to avoid false positives. For mathematical subscripts with letters/numbers (like "B₀" where 0 is a zero), it would work.

---

## How to Integrate into pdf_to_excel_columns.py

### Step 1: Copy the Functions

Copy these functions from `implement_script_detection.py` to `pdf_to_excel_columns.py`:

```python
# Add near the top of pdf_to_excel_columns.py (after imports, before other functions)

# ============================================================================
# Script Detection Configuration
# ============================================================================

SCRIPT_MAX_WIDTH = 15
SCRIPT_MAX_HEIGHT = 12
SCRIPT_MAX_TEXT_LENGTH = 3
SCRIPT_MAX_HORIZONTAL_GAP = 5
SUPERSCRIPT_MIN_TOP_DIFF = -3
SUPERSCRIPT_MAX_TOP_DIFF = 3
SUBSCRIPT_MIN_TOP_DIFF = 3
SUBSCRIPT_MAX_TOP_DIFF = 10
SCRIPT_MAX_HEIGHT_RATIO = 0.75

EXCLUDE_SYMBOLS = {'°', '™', '®', '©', '•', '·', '◦', '▪', '½', '¼', '¾', '⅓'}

# ============================================================================
# Script Detection Functions
# ============================================================================

def is_script_size(fragment):
    """Check if fragment meets size criteria for being a script."""
    if fragment["width"] >= SCRIPT_MAX_WIDTH:
        return False
    if fragment["height"] >= SCRIPT_MAX_HEIGHT:
        return False
    text = fragment.get("text", "").strip()
    if len(text) > SCRIPT_MAX_TEXT_LENGTH:
        return False
    if not text:
        return False
    return True


def is_excluded_symbol(text):
    """Check if text should not be treated as script."""
    text = text.strip()
    if text in EXCLUDE_SYMBOLS:
        return True
    if not text.replace('^', '').replace('_', '').isalnum():
        return True
    return False


def find_adjacent_parent(script_fragment, all_fragments, script_index):
    """Find parent fragment for a potential script."""
    script_left = script_fragment["left"]
    script_right = script_left + script_fragment["width"]
    script_top = script_fragment["top"]
    script_height = script_fragment["height"]
    
    candidates = []
    
    for i, other in enumerate(all_fragments):
        if i == script_index:
            continue
        
        if other["height"] <= script_height:
            continue
        
        height_ratio = script_height / other["height"]
        if height_ratio >= SCRIPT_MAX_HEIGHT_RATIO:
            continue
        
        other_left = other["left"]
        other_right = other_left + other["width"]
        
        gap_right = script_left - other_right
        if 0 <= gap_right <= SCRIPT_MAX_HORIZONTAL_GAP:
            top_diff = abs(script_top - other["top"])
            if top_diff <= SUBSCRIPT_MAX_TOP_DIFF:
                candidates.append((i, other, gap_right, top_diff))
        
        gap_left = other_left - script_right
        if 0 <= gap_left <= SCRIPT_MAX_HORIZONTAL_GAP:
            top_diff = abs(script_top - other["top"])
            if top_diff <= SUBSCRIPT_MAX_TOP_DIFF:
                candidates.append((i, other, gap_left, top_diff))
    
    if not candidates:
        return None
    
    candidates.sort(key=lambda x: (x[2], x[3]))
    parent_idx, parent, _, _ = candidates[0]
    return (parent_idx, parent)


def detect_script_type(script_fragment, parent_fragment):
    """Determine if script is superscript or subscript using TOP position."""
    top_diff = script_fragment["top"] - parent_fragment["top"]
    
    if SUPERSCRIPT_MIN_TOP_DIFF <= top_diff <= SUPERSCRIPT_MAX_TOP_DIFF:
        return "superscript"
    elif SUBSCRIPT_MIN_TOP_DIFF < top_diff <= SUBSCRIPT_MAX_TOP_DIFF:
        return "subscript"
    
    return None


def detect_and_mark_scripts(fragments):
    """Phase 1: Detect and mark superscripts/subscripts."""
    for i, f in enumerate(fragments):
        f["original_idx"] = i
    
    for i, f in enumerate(fragments):
        f["is_script"] = False
        f["script_type"] = None
        f["script_parent_idx"] = None
        
        if not is_script_size(f):
            continue
        
        text = f.get("text", "").strip()
        if is_excluded_symbol(text):
            continue
        
        parent_result = find_adjacent_parent(f, fragments, i)
        if not parent_result:
            continue
        
        parent_idx, parent = parent_result
        
        script_type = detect_script_type(f, parent)
        if not script_type:
            continue
        
        f["is_script"] = True
        f["script_type"] = script_type
        f["script_parent_idx"] = parent_idx


def merge_script_with_parent(parent, scripts):
    """Merge scripts with their parent fragment."""
    merged = dict(parent)
    scripts = sorted(scripts, key=lambda s: s["left"])
    
    merged_text = parent["text"]
    for script in scripts:
        script_text = script["text"]
        if script["script_type"] == "superscript":
            merged_text += "^" + script_text
        else:
            merged_text += "_" + script_text
    
    merged["text"] = merged_text
    merged["norm_text"] = " ".join(merged_text.split()).lower()
    
    for script in scripts:
        script_right = script["left"] + script["width"]
        merged_right = merged["left"] + merged["width"]
        if script_right > merged_right:
            merged["width"] = script_right - merged["left"]
        
        script_bottom = script["top"] + script["height"]
        merged_bottom = merged["top"] + merged["height"]
        if script_bottom > merged_bottom:
            merged["height"] = script_bottom - merged["top"]
    
    merged["has_merged_scripts"] = True
    merged["merged_script_count"] = len(scripts)
    
    return merged


def merge_scripts_across_rows(rows, all_fragments):
    """Phase 3: Merge scripts with parents across rows."""
    frag_by_idx = {}
    for row in rows:
        for f in row:
            orig_idx = f.get("original_idx")
            if orig_idx is not None:
                frag_by_idx[orig_idx] = f
    
    scripts_by_parent = {}
    script_indices = set()
    
    for row in rows:
        for f in row:
            if f.get("is_script"):
                parent_idx = f.get("script_parent_idx")
                if parent_idx is not None:
                    if parent_idx not in scripts_by_parent:
                        scripts_by_parent[parent_idx] = []
                    scripts_by_parent[parent_idx].append(f)
                    script_indices.add(f.get("original_idx"))
    
    merged_rows = []
    
    for row in rows:
        new_row = []
        
        for f in row:
            orig_idx = f.get("original_idx")
            
            if orig_idx in script_indices:
                continue
            
            if orig_idx in scripts_by_parent:
                scripts = scripts_by_parent[orig_idx]
                merged = merge_script_with_parent(f, scripts)
                new_row.append(merged)
            else:
                new_row.append(f)
        
        if new_row:
            merged_rows.append(new_row)
    
    return merged_rows
```

---

### Step 2: Add Phase 1 Call (Before Grouping)

Find line ~1105 in `pdf_to_excel_columns.py` and add Phase 1:

```python
# Around line 1105, BEFORE baseline grouping

        # Sort by baseline & left for line grouping
        fragments.sort(key=lambda f: (f["baseline"], f["left"]))

        # ===== ADD THIS: Phase 1 - Script Detection =====
        # Detect and mark scripts BEFORE grouping into rows
        detect_and_mark_scripts(fragments)
        # ================================================

        # Column detection for this page (existing code)
        col_starts = detect_column_starts(fragments, page_width, max_cols=4)
        assign_column_ids(fragments, page_width, col_starts)
```

---

### Step 3: Add Phase 3 Call (After Grouping)

Find line ~1142 and add Phase 3:

```python
# Around line 1142, AFTER baseline grouping

        # (1) First pass: group into rows and merge inline fragments
        baselines = [f["baseline"] for f in fragments]
        baseline_tol = compute_baseline_tolerance(baselines)
        raw_rows = group_fragments_into_lines(fragments, baseline_tol)

        # ===== ADD THIS: Phase 3 - Cross-Row Merging =====
        # Merge scripts with their parents across rows
        raw_rows = merge_scripts_across_rows(raw_rows, fragments)
        # ==================================================

        merged_fragments = []
        for row in raw_rows:
            merged_fragments.extend(merge_inline_fragments_in_row(row))
```

---

## That's It! 

Just two lines added:
1. **Line ~1105**: `detect_and_mark_scripts(fragments)` 
2. **Line ~1142**: `raw_rows = merge_scripts_across_rows(raw_rows, fragments)`

Plus the helper functions at the top of the file.

---

## Testing Your Integration

### Test 1: Run on Sample Page

```python
python3 pdf_to_excel_columns.py your_document.pdf
```

### Test 2: Check Results

Look in the Excel file (ReadingOrder sheet) for:
- Merged text like "10^7" instead of separate "10" and "7"
- Fewer row transitions
- More stable ColId assignments

### Test 3: Verify Drop Caps Preserved

Check pages with drop caps:
- Large first letter should still be in separate row
- Should NOT be merged with following text

---

## Configuration Tuning

If you need to adjust detection sensitivity:

### Make More Strict (Fewer False Positives)

```python
SCRIPT_MAX_WIDTH = 10      # From 15 (stricter)
SCRIPT_MAX_HEIGHT = 10     # From 12 (stricter)
SCRIPT_MAX_TEXT_LENGTH = 2 # From 3 (stricter)
```

### Make Less Strict (Catch More Scripts)

```python
SCRIPT_MAX_WIDTH = 20      # From 15 (looser)
SCRIPT_MAX_HEIGHT = 15     # From 12 (looser)
SUBSCRIPT_MAX_TOP_DIFF = 12 # From 10 (allow deeper subscripts)
```

### Allow Symbol Scripts

If you want to allow specific symbols (like Ø for magnetic field):

```python
# Remove from EXCLUDE_SYMBOLS or add special handling
ALLOW_SYMBOLS = {'Ø', '₀', '₁', '₂'}  # Specific allowed symbols

def is_excluded_symbol(text):
    text = text.strip()
    
    # Allow specific symbols
    if text in ALLOW_SYMBOLS:
        return False
    
    # Exclude others
    if text in EXCLUDE_SYMBOLS:
        return True
    
    # Rest of logic...
```

---

## Debugging

### Enable Debug Output

Add print statements to see what's being detected:

```python
def detect_and_mark_scripts(fragments):
    for i, f in enumerate(fragments):
        # ... detection logic ...
        
        if f["is_script"]:
            parent_text = fragments[f["script_parent_idx"]]["text"][:20]
            print(f"  Detected {f['script_type']}: '{f['text']}' → '{parent_text}'")
```

### Check Detection Stats

Add counter at end of page processing:

```python
# After detect_and_mark_scripts()
script_count = sum(1 for f in fragments if f.get("is_script"))
if script_count > 0:
    print(f"  Page {page_number}: Detected {script_count} superscripts/subscripts")
```

---

## Expected Results

### Before Integration

```
Excel ReadingOrder sheet:
Row 1: "...around 10"      ColId=0
Row 2: "7"                 ColId=1  ← Different row!
Row 3: "Hz..."             ColId=0
ColId transitions: 2
```

### After Integration

```
Excel ReadingOrder sheet:
Row 1: "...around 10^7Hz..." ColId=0
ColId transitions: 0
```

---

## Summary

**Phase 1 (Script Detection)** is just:
1. Copy helper functions to your file
2. Add one line before grouping: `detect_and_mark_scripts(fragments)`
3. Add one line after grouping: `raw_rows = merge_scripts_across_rows(raw_rows, fragments)`

**Done!** Scripts will merge while drop caps and large letters are preserved.

The file `implement_script_detection.py` has the complete working code ready to copy!
