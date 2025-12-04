# Coordinate System Analysis

## Your Question About Coordinates

You've identified that there are different coordinate systems across the pipeline:

### 1. MultiMedia.xml (PyMuPDF Coordinates)
```xml
<page index="8" width="549.0" height="774.0">
  <media id="p8_img1" ... 
         x1="358.01" y1="90.00" 
         x2="481.54" y2="258.15" />
</page>
```
- **Coordinate system**: PDF points (PyMuPDF/fitz)
- **Typical page sizes**: 549x774, 595x842 (A4), 612x792 (Letter)
- **Origin**: Top-left (0, 0)

### 2. pdftohtml Output (HTML Coordinates)
```xml
<page number="6" height="1161" width="823">
  <text top="129" left="155" width="7" height="30" font="5">
    <b> </b>
  </text>
</page>
```
- **Coordinate system**: HTML scaled coordinates
- **Typical page sizes**: 823x1161 (scaled from PDF)
- **Origin**: Top-left (0, 0)
- **Scale factor**: Usually ~1.4-1.5x larger than PDF points

### 3. unified.xml (HTML Coordinates)
```xml
<page number="6" width="823.0" height="1161.0">
  <texts>
    <text ... left="155.0" top="129.0" width="7.0" height="30.0" />
  </texts>
  <media>
    <media ... x1="536.69" y1="135.00" x2="721.87" y2="387.22" />
  </media>
</page>
```
- **Coordinate system**: HTML (same as pdftohtml)
- **Media coordinates**: SHOULD be transformed from PyMuPDF → HTML

### 4. Chapter XMLs (No Coordinates)
```xml
<figure>
  <mediaobject>
    <imagedata fileref="MultiMedia/Ch0001f01.jpg"/>
  </mediaobject>
</figure>
```
- **No coordinates**: DocBook doesn't use pixel coordinates
- **This is EXPECTED and CORRECT**

## The Transformation Process

### What Should Happen

```python
# In pdf_to_unified_xml.py, lines 1614-1620:

# 1. Get page dimensions
html_page_width = 823.0   # from pdftohtml
html_page_height = 1161.0
media_page_width = 549.0   # from MultiMedia.xml
media_page_height = 774.0

# 2. Calculate scale factors
scale_x = html_page_width / media_page_width  # 823/549 = 1.499
scale_y = html_page_height / media_page_height # 1161/774 = 1.500

# 3. Transform media coordinates
media_x1_pymupdf = 358.01
media_y1_pymupdf = 90.00

media_x1_html = media_x1_pymupdf * scale_x  # 358.01 * 1.499 = 536.69
media_y1_html = media_y1_pymupdf * scale_y  # 90.00 * 1.500 = 135.00
```

### The Problem You May Be Experiencing

If media coordinates in `unified.xml` are still in PyMuPDF scale (e.g., x1="358.01" instead of x1="536.69"), then the transformation is NOT being applied!

This causes:
1. ❌ Media and text coordinates in different scales
2. ❌ Overlap detection fails (text removal doesn't work)
3. ❌ Reading order assignment incorrect
4. ❌ Media placed in wrong position relative to text

## How To Diagnose

### Step 1: Run the coordinate checker

```bash
python check_coordinate_systems.py your-document
```

This will:
- Show coordinate samples from each stage
- Calculate expected vs actual transformations
- Identify if transformation is working

### Step 2: Check page number alignment

**Important**: Your examples show different page numbers:
- MultiMedia.xml: page 8
- pdftohtml: page 6

Are these the SAME physical page? Page numbering can differ:
- MultiMedia.xml uses `index` (0-based or 1-based from PDF)
- pdftohtml uses `number` (sequential from pdftohtml)
- They may not align if PDF has blank pages, cover pages, etc.

### Step 3: Check unified.xml coordinates

```bash
# Check if media coords are in HTML scale or PyMuPDF scale
grep '<media ' your-document_unified.xml | head -5

# Example of CORRECT (HTML scale):
# <media ... x1="536.69" y1="135.00" x2="721.87" y2="387.22"/>

# Example of WRONG (still PyMuPDF scale):
# <media ... x1="358.01" y1="90.00" x2="481.54" y2="258.15"/>
```

### Step 4: Compare coordinate ranges

```bash
# Get text coordinate range
grep '<text ' your-document_unified.xml | head -20 | grep -o 'left="[^"]*"' | head -5

# Get media coordinate range
grep '<media ' your-document_unified.xml | head -20 | grep -o 'x1="[^"]*"' | head -5

# They should be in similar ranges (both using HTML scale)
```

## Possible Issues & Fixes

### Issue 1: Transformation Not Applied

**Symptom**: Media coords in unified.xml are still in PyMuPDF scale (300-500 range instead of 500-750 range)

**Cause**: The `transform_media_coords_to_html()` function not being called or conditions failing

**Check**:
```python
# In pdf_to_unified_xml.py line 1613-1620
if media_page_width > 0 and media_page_height > 0:
    transform_media_coords_to_html(...)
```

**Possible reasons**:
- `media_page_width` or `media_page_height` is 0 or None
- Transformation silently fails
- Coordinates not being read correctly from MultiMedia.xml

### Issue 2: Page Dimension Mismatch

**Symptom**: Scale factors are incorrect (e.g., 2.0 instead of 1.5)

**Cause**: Using wrong page dimensions for calculation

**Check**:
```bash
# Check if page dimensions match between files
grep '<page.*width.*height' your-document_MultiMedia.xml | head -3
grep '<page.*width.*height' your-document_unified.xml | head -3
```

### Issue 3: Coordinate System Confusion

**Symptom**: Images appear in wrong locations or text removal fails

**Cause**: Mixing coordinate systems during processing

**The pipeline should maintain**:
- MultiMedia.xml: PyMuPDF coords (549x774)
- unified.xml: HTML coords (823x1161) ← TRANSFORMED
- All calculations in unified.xml use HTML coords

## Why Chapter XMLs Have No Coordinates

This is **EXPECTED and CORRECT**!

DocBook XML is a semantic markup format:
```xml
<!-- This is correct DocBook -->
<figure>
  <title>Figure 1.1 - System Architecture</title>
  <mediaobject>
    <imageobject>
      <imagedata fileref="MultiMedia/Ch0001f01.jpg"/>
    </imageobject>
  </mediaobject>
</figure>
```

DocBook doesn't include pixel coordinates because:
- ✅ It's layout-agnostic (rendered by different systems)
- ✅ Images are placed by rendering engine
- ✅ Position is determined by document flow
- ✅ Coordinates would be meaningless in final output (HTML, PDF, EPUB)

## What To Do Next

1. **Run the diagnostic**:
   ```bash
   python check_coordinate_systems.py your-document
   ```

2. **Check the output** for:
   - Are media coords transformed in unified.xml?
   - Do media and text coords use same scale?
   - Are there any warnings about coordinates outside page bounds?

3. **If transformation is NOT working**:
   - Check if `media_page_width` and `media_page_height` are being read correctly
   - Verify the condition on line 1613 is passing
   - Add debug logging to see what values are being used

4. **If transformation IS working but images still missing**:
   - The issue is elsewhere (filtering, file paths, etc.)
   - Run `trace_missing_images.py` to find where images are lost

## Key Takeaway

**Two coordinate systems are fine, AS LONG AS:**
✅ MultiMedia.xml uses PyMuPDF coords (549x774)
✅ unified.xml uses HTML coords (823x1161) - **transformed!**
✅ All processing in unified.xml uses same scale
✅ Chapter XMLs have no coords (DocBook doesn't use them)

The transformation from PyMuPDF → HTML happens in `create_unified_xml()` function and should be working. If it's not, that's a bug we need to fix!

Run the diagnostic tool to verify: `python check_coordinate_systems.py your-document`
