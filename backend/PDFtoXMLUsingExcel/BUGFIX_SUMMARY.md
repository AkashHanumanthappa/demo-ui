# Bug Fix Summary - heuristics_Nov3.py

## Issue
The heuristics processing was failing with a `NameError: name 'lines' is not defined` at line 2840.

## Root Cause
The main processing loop in `label_blocks()` iterates over a variable called `entries` (defined at line 2215), but the list detection code was incorrectly referencing a non-existent variable named `lines`.

## Changes Made

### 1. Fixed Variable References (Lines 2840-2850)
**Before:**
```python
is_list, list_type, num_items = _detect_list_sequence(lines, idx, mapping)
# ...
for list_idx in range(idx, min(idx + num_items, len(lines))):
    list_line = lines[list_idx]
```

**After:**
```python
is_list, list_type, num_items = _detect_list_sequence(entries, idx, mapping)
# ...
for list_idx in range(idx, min(idx + num_items, len(entries))):
    list_line = _line_of(entries[list_idx])
```

### 2. Updated `_detect_list_sequence()` Function (Lines 1567-1631)
Modified the function to accept `entries` (list of dictionaries) instead of `lines` (list of Line objects):

- Changed parameter from `lines: Sequence[Line]` to `entries: Sequence`
- Added logic to skip non-text/line entries
- Used `_line_of()` helper to convert entry dictionaries to Line objects
- Updated all internal references to use the new entry-based approach

### 3. Updated Documentation (Line 2044)
Updated the function signature comment from:
```python
- _detect_list_sequence(lines, start_idx, mapping) -> (is_list: bool, list_type: str, num_items: int)
```
to:
```python
- _detect_list_sequence(entries, start_idx, mapping) -> (is_list: bool, list_type: str, num_items: int)
```

## SyntaxWarning Note
The warning about `"\s"` escape sequence on line 1099 is on a commented-out line and does not affect execution. It can be safely ignored.

## Testing
The fixes ensure that:
1. List detection properly accesses the `entries` variable that exists in scope
2. Entry dictionaries are correctly converted to Line objects using `_line_of()`
3. The function handles mixed entry types (text, line, image, table, etc.) gracefully

## Result
The `NameError` is resolved, and the heuristics processing should now complete successfully.
