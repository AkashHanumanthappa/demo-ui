# Changes Summary - Script Detection Implementation

## Overview

**File Modified**: `pdf_to_excel_columns.py`  
**Lines Added**: ~340 lines  
**Breaking Changes**: None  
**Integration Points**: 2 locations  

---

## Detailed Changes

### 1. Configuration Constants (Lines 12-30)

**Added 19 lines** of configuration:

```python
# Script Detection Configuration
SCRIPT_MAX_WIDTH = 15
SCRIPT_MAX_HEIGHT = 12
SCRIPT_MAX_TEXT_LENGTH = 3
SCRIPT_MAX_HORIZONTAL_GAP = 5
SUPERSCRIPT_MIN_TOP_DIFF = -3
SUPERSCRIPT_MAX_TOP_DIFF = 3
SUBSCRIPT_MIN_TOP_DIFF = 3
SUBSCRIPT_MAX_TOP_DIFF = 10
SCRIPT_MAX_HEIGHT_RATIO = 0.75
EXCLUDE_SYMBOLS = {...}
```

**Purpose**: Configurable thresholds for detecting superscripts/subscripts

---

### 2. Helper Functions (Lines 33-328)

**Added ~295 lines** of helper functions:

#### Detection Functions
```python
def is_script_size(fragment)           # Check if fragment is tiny
def is_excluded_symbol(text)           # Exclude bullets, symbols
def find_adjacent_parent(...)          # Find parent using TOP position
def detect_script_type(...)            # Determine super vs subscript
def detect_and_mark_scripts(...)       # PHASE 1: Main detection
```

#### Merging Functions
```python
def merge_script_with_parent(...)      # Merge scripts with parent
def merge_scripts_across_rows(...)     # PHASE 3: Cross-row merge
```

**Purpose**: Core script detection and merging logic

---

### 3. Phase 1 Integration (Line ~1426-1432)

**Added 7 lines** before column detection:

```python
# Sort by baseline & left for line grouping
fragments.sort(key=lambda f: (f["baseline"], f["left"]))

# ===== Phase 1: Detect superscripts/subscripts =====  ← NEW
script_count = detect_and_mark_scripts(fragments)      ← NEW
if script_count > 0:                                   ← NEW
    print(f"  Page {page_number}: Detected {script_count} superscript(s)/subscript(s)")  ← NEW

# Column detection for this page (existing code continues...)
```

**Purpose**: Detect and mark scripts before grouping into rows

---

### 4. Phase 3 Integration (Line ~1471-1474)

**Added 4 lines** after baseline grouping:

```python
raw_rows = group_fragments_into_lines(fragments, baseline_tol)

# ===== Phase 3: Merge scripts across rows =====       ← NEW
raw_rows = merge_scripts_across_rows(raw_rows, fragments)  ← NEW

merged_fragments = []
for row in raw_rows:
    merged_fragments.extend(merge_inline_fragments_in_row(row))
```

**Purpose**: Merge detected scripts with their parents across rows

---

## Visual Diff Summary

```diff
pdf_to_excel_columns.py

@@ Line 10 @@
 import statistics
 
+# -------------------------------------------------------------
+# Script Detection Configuration (Superscripts/Subscripts)
+# -------------------------------------------------------------
+SCRIPT_MAX_WIDTH = 15
+... (19 lines of configuration)
+
+# -------------------------------------------------------------
+# Script Detection Functions (Phase 1)
+# -------------------------------------------------------------
+def is_script_size(fragment):
+    ... (295 lines of helper functions)
+
 # -------------------------------------------------------------
 # pdftohtml -xml runner
 # -------------------------------------------------------------

@@ Line ~1424 @@
 fragments.sort(key=lambda f: (f["baseline"], f["left"]))
 
+# ===== Phase 1: Detect superscripts/subscripts =====
+script_count = detect_and_mark_scripts(fragments)
+if script_count > 0:
+    print(f"  Page {page_number}: Detected {script_count} superscript(s)/subscript(s)")
+
 # Column detection for this page

@@ Line ~1469 @@
 raw_rows = group_fragments_into_lines(fragments, baseline_tol)
 
+# ===== Phase 3: Merge scripts across rows =====
+raw_rows = merge_scripts_across_rows(raw_rows, fragments)
+
 merged_fragments = []
```

**Total**: ~340 lines added, 0 lines removed

---

## Impact on Existing Code

### Unchanged Functions ✓
- `run_pdftohtml_xml()` - No changes
- `compute_baseline_tolerance()` - No changes
- `group_fragments_into_lines()` - No changes ← **KEY: Baseline grouping preserved**
- `merge_inline_fragments_in_row()` - No changes
- `assign_column_ids()` - No changes
- `detect_column_starts()` - No changes
- All other functions - No changes

### Modified Behavior
- **Fragment count**: Slightly fewer (scripts merged with parents)
- **Text content**: Now includes "^" and "_" notation
- **Terminal output**: Added detection messages

### Zero Breaking Changes
- All existing logic preserved
- Baseline grouping unchanged
- Drop caps behavior unchanged
- ColId assignment logic unchanged (just better input)

---

## Before & After Example

### Input (from pdftohtml XML)
```xml
<text top="191" left="101" width="428" height="18">...around 10</text>
<text top="192" left="529" width="5" height="11">7</text>
<text top="191" left="534" width="166" height="18">Hz...</text>
```

### Before This Fix
```
Processing:
  Fragment 1: "...around 10" (baseline=209) → Row 1, ColId=0
  Fragment 2: "7" (baseline=203)            → Row 2, ColId=1 ← Different row!
  Fragment 3: "Hz..." (baseline=209)        → Row 1, ColId=0

Output:
  Row 1: "...around 10", "Hz..."
  Row 2: "7"
  
ColId sequence: [0, 1, 0] ← Weaving!
```

### After This Fix
```
Processing:
  Phase 1: Detected "7" as superscript of "...around 10"
  Phase 2: Grouped into rows using baseline
  Phase 3: Merged "7" → "...around 10^7"
  Inline merge: "...around 10^7Hz..."

Output:
  Row 1: "...around 10^7Hz..."
  
ColId sequence: [0] ← No weaving!
```

---

## Ready to Go! 🚀

Your surgical fix is implemented and ready for testing.

**Next steps**:
1. Test on your documents
2. Review Excel output
3. Create PR using `SUGGESTED_COMMIT_MESSAGE.txt`
4. Monitor after merge

**The fix is in place!** 🎉
