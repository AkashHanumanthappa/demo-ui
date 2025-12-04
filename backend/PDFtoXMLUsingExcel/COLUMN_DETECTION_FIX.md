# Column Detection Fix - Single Column Pages with Line Continuations

## Problem Summary

**Issue**: Page 19 (and similar single-column pages) was being incorrectly split across multiple columns (ColID 1, ColID 0, and ColID 2), causing text to be read out of order.

### Example from Page 19

The text was incorrectly split:
- ColID 0: "(or within) a large external magnetic field (called B"
- ColID 2: ") will align with the external field. Un-"  ← **Same baseline, same line!**

This is clearly one continuous line being incorrectly treated as two separate columns.

## Root Cause

The `detect_column_starts()` function was clustering fragments by horizontal position (x-coordinate) without considering **vertical extent**. This caused:

1. **Line continuations** at x~438-625 to be treated as a separate column
2. These were only 4 fragments across 2 lines (not a real column!)
3. True columns span many lines vertically (15+ lines typically)

### Position Analysis

```
ColID 0 (correct): 21 fragments, left 101-128, spanning full page height
ColID 1 (correct): 20 fragments, headers/captions at various positions  
ColID 2 (WRONG!):  4 fragments, left 438-625, only 2 unique baselines
                   ↑ These are line continuations, NOT a column!
```

## Solution

Added **vertical extent validation** to `detect_column_starts()`:

```python
# A true column should have fragments at many different vertical positions (baselines)
# Line continuations typically only appear on a few lines
min_unique_baselines = 5  # A column should span at least 5 different lines
baseline_tolerance = 2.0  # Group baselines within 2 pixels as same line

# For each detected cluster, count unique baseline groups
for cluster, cluster_frags in zip(clusters, cluster_fragments):
    baselines = sorted(set(f["baseline"] for f in cluster_frags))
    
    # Group baselines within tolerance to count unique lines
    unique_baseline_groups = []
    for b in baselines:
        found = False
        for group in unique_baseline_groups:
            if abs(b - group[0]) <= baseline_tolerance:
                group.append(b)
                found = True
                break
        if not found:
            unique_baseline_groups.append([b])
    
    num_unique_lines = len(unique_baseline_groups)
    
    # Only keep clusters with sufficient vertical distribution
    if num_unique_lines >= min_unique_baselines:
        valid_clusters.append(cluster)
```

### Key Changes

1. **Track fragments** for each cluster (not just x-positions)
2. **Count unique baselines** within each cluster
3. **Filter out clusters** with fewer than 5 unique baselines
4. **Treat as single column** if no valid clusters remain

## Test Results

### Page 19 (Single Column with Line Continuations)
- **Before**: Detected 3 columns (incorrect)
- **After**: Detected 1 column ✓ PASS

### Multi-Column Pages
- **2-column page**: Detected 2 columns ✓ PASS
- **3-column page**: Detected 3 columns ✓ PASS
- **Single column + 3 line continuations**: Detected 1 column ✓ PASS

## Impact

This fix ensures:
1. ✓ Single-column pages are correctly identified (no false column splits)
2. ✓ Multi-column pages still work correctly (2-col, 3-col layouts preserved)
3. ✓ Line continuations are NOT treated as separate columns
4. ✓ Headers, captions, and figure labels don't create false columns

## Files Modified

- `pdf_to_excel_columns.py`: Updated `detect_column_starts()` function (lines 369-523)

## Testing

Run the test scripts to verify:

```bash
# Test the specific page 19 issue
python3 test_page19_column_fix.py

# Test multi-column detection still works
python3 test_multicolumn_detection.py
```

Both should show all tests passing.
