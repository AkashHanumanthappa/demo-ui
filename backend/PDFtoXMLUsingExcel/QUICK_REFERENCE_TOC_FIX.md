# Quick Reference: TOC.xml Font Size Fix

## TL;DR

✅ **Fixed**: TOC.xml was showing 0 font size for all text - now shows correct sizes
✅ **Location**: `font_roles_auto.py` - `extract_toc_section()` function
✅ **Test**: Run `python3 test_toc_font_size_fix.py` to verify

## The Problem

```xml
<!-- BEFORE (BROKEN) -->
<entry size="0">Chapter 1: Introduction ......... 1</entry>
<entry size="0">Chapter 2: Methods .............. 15</entry>
```

## The Fix

```xml
<!-- AFTER (FIXED) -->
<entry size="12.0" family="TimesNewRoman">Chapter 1: Introduction ......... 1</entry>
<entry size="12.0" family="TimesNewRoman">Chapter 2: Methods .............. 15</entry>
```

## Root Cause

The `extract_toc_section()` function was reading font size directly from text elements:
- Text elements have `font="ID"` (reference to fontspec)
- Font size is stored in `<fontspec id="ID" size="12" .../>` elements
- Need to look up: `text.font → fontspec[ID].size`

The function was missing this lookup, so always got 0 as default.

## What Changed

### File: `font_roles_auto.py`

**Function signature** (line 57):
```python
def extract_toc_section(
    root: ET.Element,
    toc_start_size: float,
    toc_start_page: int,
    output_path: str,
    font_info_map: Dict[str, Dict[str, Any]]  # NEW: Added this parameter
) -> Dict[str, Any]:
```

**Font size lookup** (lines 102-110):
```python
# BEFORE (WRONG):
font_size = _f(text_elem.get("font_size") or text_elem.get("size", "0"))

# AFTER (CORRECT):
font_id = text_elem.get("font")
if font_id in font_info_map:
    font_size = font_info_map[font_id]["size"]
    font_family = font_info_map[font_id]["family"]
else:
    font_size = _f(text_elem.get("font_size") or text_elem.get("size", "0"))
    font_family = "Unknown"
```

**Function call** (line 381):
```python
# BEFORE:
toc_info = extract_toc_section(root, toc_heading_size, toc_heading_page, toc_output_path)

# AFTER:
toc_info = extract_toc_section(root, toc_heading_size, toc_heading_page, toc_output_path, font_info_map)
```

## Impact

### ✅ Fixed
- TOC.xml has correct font sizes
- TOC boundary detection works (stops at chapter headings)
- Chapter breakup logic can use TOC.xml
- Font role analysis is accurate

### 📊 Enhanced
- Added font family information to TOC entries
- Better metadata for structure analysis

## Testing

```bash
# Run automated test
python3 test_toc_font_size_fix.py

# Or test with actual PDF
python3 pdf_to_unified_xml.py your_book.pdf --full-pipeline
cat your_book_TOC.xml | grep 'size="'

# Should see non-zero sizes like:
# <entry size="14.0" family="TimesNewRoman-Bold">Table of Contents</entry>
# <entry size="12.0" family="TimesNewRoman">Chapter 1 ........ 1</entry>
```

## Pipeline Flow (Updated)

```
PDF
 ↓
[pdf_to_unified_xml.py]
 ↓ Creates unified XML with <fontspec> elements
 ├── *_unified.xml (has font IDs, not sizes)
 └── *_MultiMedia/ folder
     ↓
[font_roles_auto.py] ← FIXED HERE
 ↓ Now correctly looks up font sizes
 ├── *_font_roles.json
 └── *_TOC.xml (NOW HAS CORRECT SIZES ✅)
     ↓
[heuristics_Nov3.py]
 ↓ Can use TOC.xml for chapter detection
 └── *_structured.xml
     ↓
[create_book_package.py]
 ↓ Splits into chapters
 └── *.zip package
```

## For Debugging

If you still see 0 font sizes in TOC.xml:

1. **Check unified XML has fontspec elements**:
   ```bash
   grep '<fontspec' your_book_unified.xml
   ```
   Should see: `<fontspec id="0" size="12" family="..." />`

2. **Check text elements have font attributes**:
   ```bash
   grep '<text font=' your_book_unified.xml | head
   ```
   Should see: `<text font="0" ...>`

3. **Verify font_info_map is built**:
   ```python
   # In font_roles_auto.py, add after line 192:
   print(f"DEBUG: font_info_map = {font_info_map}")
   ```

4. **Check TOC extraction gets map**:
   ```python
   # In extract_toc_section(), add after line 102:
   print(f"DEBUG: font_id={font_id}, font_size={font_size}")
   ```

## Related Files

- ✅ **Modified**: `font_roles_auto.py` (the fix)
- 📖 **Docs**: `TOC_FONT_SIZE_ISSUE_ANALYSIS.md` (detailed analysis)
- 📖 **Docs**: `TOC_FIX_SUMMARY.md` (fix summary)
- 📖 **Docs**: `PIPELINE_OVERVIEW_AND_FIX.md` (complete overview)
- 🧪 **Test**: `test_toc_font_size_fix.py` (verification)

## Questions?

See `PIPELINE_OVERVIEW_AND_FIX.md` for complete architecture and flow.
