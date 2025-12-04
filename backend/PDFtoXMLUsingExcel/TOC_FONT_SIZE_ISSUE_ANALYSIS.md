# TOC.xml Font Size Issue - Root Cause Analysis

## Problem Summary

The `TOC.xml` file is showing **0 font size for all text entries**, which breaks:
1. TOC extraction boundary detection (relies on font size comparison)
2. Chapter breakup logic that uses TOC.xml
3. Any downstream processing depending on font size information

## Root Cause

The issue is in `font_roles_auto.py` in the `extract_toc_section()` function.

### How Font Information Works in the Pipeline

#### 1. PDF to Unified XML (`pdf_to_unified_xml.py`)

When creating the unified XML, the pipeline:

1. **Copies `<fontspec>` elements** from pdftohtml XML to the unified XML root (lines 821-824):
   ```xml
   <fontspec id="0" size="12" family="TimesNewRoman" color="#000000"/>
   <fontspec id="1" size="14" family="TimesNewRoman-Bold" color="#000000"/>
   <fontspec id="2" size="10" family="Arial" color="#000000"/>
   ```

2. **Text elements get a `font` attribute** (font ID reference), not direct size (line 936-940):
   ```xml
   <text font="0" ...>Some text</text>
   <text font="1" ...>Heading text</text>
   ```

The font size is **NOT stored directly** in text elements - it must be looked up via the `font` attribute → `fontspec` mapping.

#### 2. Font Roles Auto (`font_roles_auto.py`)

The script has TWO functions that read font sizes:

##### ✅ **CORRECT: `analyze_fonts()` function (lines 218-233)**

```python
for text_elem in page_elem.findall(".//text"):
    font_id = text_elem.get("font")
    
    # CORRECT: Look up font size from font_info_map
    if font_id in font_info_map:
        font_info = font_info_map[font_id]
        size = font_info["size"]  # Gets actual size from fontspec
        family = font_info["family"]
    else:
        # Fallback only if font ID not found
        size_hint = text_elem.get("font_size") or text_elem.get("size")
        size = _f(size_hint)
```

This correctly:
1. Extracts the `font` attribute (font ID)
2. Looks it up in `font_info_map` (built from `<fontspec>` elements)
3. Gets the actual font size from the fontspec

##### ❌ **INCORRECT: `extract_toc_section()` function (line 101)**

```python
for text_elem in page_elem.findall(".//text"):
    text_content = "".join(text_elem.itertext()).strip()
    
    # WRONG: Tries to get font size directly from text element
    font_size = _f(text_elem.get("font_size") or text_elem.get("size", "0"))
    # This will ALWAYS return 0 because text elements don't have font_size/size attributes!
```

This function:
1. **Does NOT use `font_info_map`** at all
2. Tries to read `font_size` or `size` directly from text elements (which don't exist)
3. Always gets 0 as the default value
4. Writes all TOC entries with `size="0"`

### Why This Breaks Things

1. **TOC Boundary Detection**: The function tries to stop extracting TOC when it finds text with size >= `toc_start_size` (line 122), but since all sizes are 0, this never works correctly.

2. **Chapter Breakup**: Any downstream code trying to use TOC.xml for chapter detection gets nonsense font size data.

3. **Font Role Analysis**: The TOC font sizes are wrong in the output, making it hard to understand document structure.

## The Fix

The `extract_toc_section()` function needs to:

1. **Accept `font_info_map` as a parameter**
2. **Look up font sizes the same way `analyze_fonts()` does**:
   ```python
   # Get font ID from text element
   font_id = text_elem.get("font")
   
   # Look up font size from font_info_map
   if font_id in font_info_map:
       font_size = font_info_map[font_id]["size"]
   else:
       # Fallback to direct attribute (for edge cases)
       font_size = _f(text_elem.get("font_size") or text_elem.get("size", "0"))
   ```

3. **Update the call site in `analyze_fonts()`** to pass `font_info_map`

## Impact

This is a **critical bug** that affects:
- ✅ Font statistics collection (works correctly)
- ❌ TOC extraction (broken - all sizes are 0)
- ❌ Chapter detection from TOC (broken - relies on TOC.xml)
- ❌ Document structure analysis (broken - wrong font sizes in TOC)

## Files to Modify

1. **`font_roles_auto.py`**:
   - Update `extract_toc_section()` signature to accept `font_info_map`
   - Update font size lookup logic to use `font_info_map`
   - Update call to `extract_toc_section()` in `analyze_fonts()` to pass `font_info_map`
