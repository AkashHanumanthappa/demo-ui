# Quick Start: Fix ColId Weaving Issues

## 5-Minute Quick Start

### Step 1: Analyze Your Document (2 minutes)

```bash
# Generate Excel file
python3 pdf_to_excel_columns.py your_document.pdf

# Check for weaving issues
python3 analyze_colid_weaving.py your_document_columns.xlsx
```

**Look for**:
- "Weaving detected: YES"
- High transition counts (>3)
- Pages with many ReadingOrderBlocks

### Step 2: Test the Fix (1 minute)

```bash
# Run test suite to verify fix works
python3 test_colid_fix.py
```

**Expected**: 5/6 tests pass (83% or better)

### Step 3: Apply the Fix (2 minutes)

Edit `pdf_to_excel_columns.py`:

**Find line 1114** (around the middle of the file):
```python
assign_column_ids(fragments, page_width, col_starts)
```

**Replace with**:
```python
# Import at top of file
from fix_colid_weaving import improved_assign_column_ids

# At line 1114, replace with:
improved_assign_column_ids(
    fragments, 
    page_width, 
    col_starts,
    enable_single_column_detection=True,
    enable_smoothing=True,
    single_column_colid=1
)
```

**OR** copy-paste the fix functions directly (see COLID_WEAVING_SOLUTION.md).

### Step 4: Regenerate and Verify (< 1 minute)

```bash
# Backup original
mv your_document_columns.xlsx your_document_columns_backup.xlsx

# Regenerate with fix
python3 pdf_to_excel_columns.py your_document.pdf

# Verify fix
python3 analyze_colid_weaving.py your_document_columns.xlsx
```

**Expected improvements**:
- Weaving: NO (instead of YES)
- Transitions: 0-1 (instead of 5-10+)
- Unified ReadingOrderBlocks

---

## Command Reference

### Analyze Weaving Patterns

```bash
# All pages overview
python3 analyze_colid_weaving.py document_columns.xlsx

# Specific page detail
python3 analyze_colid_weaving.py document_columns.xlsx --page 19

# Show assignment logic
python3 analyze_colid_weaving.py document_columns.xlsx --page 19 --logic
```

### Test Fix

```bash
# Run all tests
python3 test_colid_fix.py

# Expected: 5/6 pass (83%+)
```

### Apply Fix Options

**Option 1: Import (Recommended)**
```python
from fix_colid_weaving import improved_assign_column_ids
improved_assign_column_ids(fragments, page_width, col_starts)
```

**Option 2: Copy Functions**
Copy these from `fix_colid_weaving.py`:
- `is_single_column_page()`
- `smooth_colid_transitions()`
- `assign_single_column_ids()`

**Option 3: Inline Patch**
Add at end of `assign_column_ids()`:
```python
# Single-column detection
if len(col_starts) <= 1 or is_single_column_page(...):
    for f in fragments:
        f["col_id"] = 1
    return
```

---

## Troubleshooting

### "Still seeing weaving after fix"

1. Check fix was applied correctly
2. Run test: `python3 test_colid_fix.py`
3. Verify page is truly single-column
4. Check column detection: may have genuine multi-column

### "Multi-column pages broken"

1. Check if single-column threshold too high
2. Disable single-column detection:
   ```python
   improved_assign_column_ids(..., enable_single_column_detection=False)
   ```
3. Adjust criteria in `is_single_column_page()`

### "Fix not working on specific page"

1. Analyze specific page: `--page N --logic`
2. Check column starts detected
3. May need manual adjustment for edge case
4. Consider adjusting detection criteria

---

## Key Files

- **`analyze_colid_weaving.py`**: Diagnostic tool
- **`fix_colid_weaving.py`**: Implementation of fix
- **`test_colid_fix.py`**: Test suite
- **`COLID_WEAVING_SOLUTION.md`**: Full documentation
- **`COLID_WEAVING_VISUAL_EXAMPLE.md`**: Visual examples
- **`COLID_ANALYSIS_GUIDE.md`**: Analysis methodology

---

## Success Criteria

✅ **Before Fix**:
- Weaving detected: YES
- Transitions: 8-12+
- ReadingOrderBlocks: 4-8

✅ **After Fix**:
- Weaving detected: NO
- Transitions: 0-1
- ReadingOrderBlocks: 1-2

✅ **Multi-column preserved**:
- Two-column pages: Still ColId 1 & 2
- Full-width headers: Still ColId 0
- Reading order: Correct

---

## Next Steps

1. ✅ Test on your document
2. ✅ Verify single-column pages fixed
3. ✅ Verify multi-column pages unchanged
4. ✅ Check downstream processing (XML generation)
5. ✅ Deploy to production

For detailed documentation, see:
- `COLID_WEAVING_SOLUTION.md` - Complete solution guide
- `COLID_WEAVING_VISUAL_EXAMPLE.md` - Visual examples
- `COLID_ANALYSIS_GUIDE.md` - Analysis methodology
