# PDF to DocBook Pipeline - Overview and TOC.xml Fix

## Complete Pipeline Architecture

### Phase 1: PDF Extraction and Unified XML Creation

**Script**: `pdf_to_unified_xml.py`

**Process**:
1. **Text Extraction** (`pdf_to_excel_columns.py`):
   - Extracts text with column detection
   - Assigns reading order and paragraph grouping
   - Preserves font IDs (references to fontspec)

2. **Media Extraction** (`Multipage_Image_Extractor.py`):
   - Extracts images, vectors, and tables
   - Preserves bounding box coordinates
   - Creates `*_MultiMedia/` folder

3. **Merging** (`merge_text_and_media_simple()`):
   - Removes text inside table cells (already in table XML)
   - Assigns reading order to media based on position
   - Creates merged page structure

4. **Unified XML Generation** (`create_unified_xml()`):
   - **Copies `<fontspec>` elements** from pdftohtml XML to document root
   - Creates hierarchical structure: `<document><page><texts><para><text>`
   - Text elements have `font="ID"` attribute (NOT direct font_size)
   - Includes media and table elements with reading order
   - Output: `*_unified.xml`

**Key Structure**:
```xml
<document source="book.pdf">
  <!-- Font definitions at root -->
  <fontspec id="0" size="12" family="TimesNewRoman" color="#000000"/>
  <fontspec id="1" size="14" family="TimesNewRoman-Bold" color="#000000"/>
  
  <page number="1" width="612" height="792">
    <texts>
      <para col_id="0" reading_block="1">
        <!-- Text elements reference font by ID -->
        <text font="0" reading_order="1" ...>Body text</text>
        <text font="1" reading_order="2" ...>Heading text</text>
      </para>
    </texts>
    <media>...</media>
    <tables>...</tables>
  </page>
</document>
```

### Phase 2: Font Role Analysis and TOC Extraction

**Script**: `font_roles_auto.py`

**Process**:
1. **Build Font Info Map**:
   ```python
   font_info_map = {}
   for fontspec in root.findall(".//fontspec"):
       font_id = fontspec.get("id")
       font_info_map[font_id] = {
           "size": float(fontspec.get("size")),
           "family": fontspec.get("family"),
           "color": fontspec.get("color")
       }
   ```

2. **Analyze Font Usage** (`analyze_fonts()`):
   - Iterates through all `<text>` elements
   - **Looks up font size using**: `font_id → font_info_map[font_id]["size"]`
   - Collects statistics: size distribution, page counts, font families
   - Detects "Table of Contents" heading and its font size

3. **Derive Font Roles**:
   - Identifies most common size (body text)
   - Assigns roles: book.title, chapter, section, subsection, paragraph
   - Based on: size relative to body, occurrence count, page distribution

4. **Extract TOC Section** (`extract_toc_section()` - **FIXED**):
   - Starts from "Table of Contents" heading
   - **Now correctly uses `font_info_map`** to look up font sizes
   - Continues until finding text with size >= TOC heading size
   - Outputs: `*_TOC.xml` with correct font sizes

5. **Output**: `*_font_roles.json` and `*_TOC.xml`

### Phase 3: Heuristics and DocBook Conversion

**Script**: `heuristics_Nov3.py`

**Process**:
1. **Block Extraction** (`label_blocks()`):
   - Reads unified XML and font roles JSON
   - Extracts PDF bookmarks for chapter detection
   - Labels text blocks: book_title, chapter, section, subsection, paragraph, etc.
   - Handles special content: tables, figures, lists, footnotes, index

2. **DocBook Conversion** (`blocks_to_docbook_xml()`):
   - Converts labeled blocks to DocBook structure
   - Creates proper hierarchy: `<book><chapter><section><para>`
   - Handles cross-references and figure labels
   - Preserves formatting and emphasis

3. **Output**: `*_structured.xml` (DocBook format)

### Phase 4: Packaging

**Script**: `create_book_package.py`

**Process**:
1. **Chapter Splitting** (in `package.py`):
   - Splits book into separate chapter files
   - Collects media references from each chapter
   - Creates proper cross-references between chapters

2. **ZIP Creation**:
   - Packages all chapter XMLs
   - Includes media files (from `*_MultiMedia/` folder)
   - Adds DTD and catalog files
   - Creates validation structure

3. **Output**: `*.zip` deliverable package

---

## The TOC.xml Font Size Bug (NOW FIXED)

### What Was Broken

In `font_roles_auto.py`, the `extract_toc_section()` function was trying to read font size directly:

```python
# WRONG - text elements don't have font_size attribute
font_size = _f(text_elem.get("font_size") or text_elem.get("size", "0"))
# Always returned 0!
```

### Why It Was Broken

1. Text elements in unified XML have `font="ID"` attribute, NOT `font_size`
2. Font sizes are stored in `<fontspec>` elements at document root
3. Must look up: `text.font → fontspec[font].size`

### The Fix

Updated `extract_toc_section()` to use the same lookup logic as `analyze_fonts()`:

```python
# Get font ID from text element
font_id = text_elem.get("font")

# Look up font size from font_info_map
if font_id in font_info_map:
    font_size = font_info_map[font_id]["size"]
    font_family = font_info_map[font_id]["family"]
else:
    # Fallback for edge cases
    font_size = _f(text_elem.get("font_size") or text_elem.get("size", "0"))
    font_family = "Unknown"
```

### What's Fixed

✅ **TOC.xml now has correct font sizes** - All entries show actual sizes (not 0)
✅ **Boundary detection works** - Stops at correct chapter heading based on font size
✅ **Enhanced metadata** - Added font family information to entries
✅ **Chapter breakup ready** - TOC.xml can be used for document structure analysis

### Test Results

```bash
$ python3 test_toc_font_size_fix.py

======================================================================
✓ TEST PASSED: All TOC entries have correct font sizes
======================================================================

Entry 1: size=14.0, family=TimesNewRoman-Bold, text='Table of Contents'
  ✓ Font size is correct
Entry 2: size=12.0, family=TimesNewRoman, text='Chapter 1: Introduction ......... 1'
  ✓ Font size is correct
Entry 3: size=12.0, family=TimesNewRoman, text='Chapter 2: Methods .............. 15'
  ✓ Font size is correct

✓ TOC extraction stopped at correct boundary (page 3, chapter heading)
```

---

## How Chapter Breakup Currently Works

### Current Implementation (heuristics_Nov3.py)

**Method 1: PDF Bookmarks** (Primary)
- Extracts bookmarks from PDF using PyPDF2
- Creates chapter boundaries based on bookmark structure
- Most reliable when PDF has proper bookmarks

**Method 2: Font Size Heuristics** (Fallback)
- Identifies chapter headings based on:
  - Font size larger than body text
  - Position on page (typically near top)
  - Pattern matching (e.g., "Chapter X", "CHAPTER X")
- Creates chapters when heading patterns detected

**Method 3: Default Single Chapter** (Last Resort)
- If no bookmarks or chapter headings detected
- Creates a single chapter with all content

### Future Enhancement: TOC-Based Chapter Detection

Now that TOC.xml has correct font sizes, it can be used for:

1. **Validating bookmark-based chapters**:
   - Cross-reference TOC entries with detected chapters
   - Ensure chapter titles match TOC

2. **Alternative chapter detection**:
   - Parse TOC entries to find chapter references
   - Extract page numbers from TOC
   - Create chapter boundaries based on TOC structure

3. **Chapter title extraction**:
   - Use TOC entries as source of truth for chapter titles
   - Handle cases where heading text is split across lines

**Implementation would be in `heuristics_Nov3.py`**:
```python
def _extract_chapters_from_toc(toc_xml_path: str) -> List[dict]:
    """Extract chapter information from TOC.xml."""
    # Parse TOC.xml
    # Extract entries matching chapter pattern
    # Get page numbers from TOC entries
    # Create chapter boundaries
    # Return list of chapter definitions
```

---

## Files Modified in This Fix

1. **`font_roles_auto.py`**:
   - Line 57-63: Updated `extract_toc_section()` signature
   - Line 102-110: Fixed font size lookup using `font_info_map`
   - Line 116-119, 147-150: Added font family to TOC entries
   - Line 381: Updated function call to pass `font_info_map`

2. **Documentation**:
   - `TOC_FONT_SIZE_ISSUE_ANALYSIS.md` - Root cause analysis
   - `TOC_FIX_SUMMARY.md` - Fix summary and impact
   - `PIPELINE_OVERVIEW_AND_FIX.md` - This comprehensive overview

3. **Testing**:
   - `test_toc_font_size_fix.py` - Unit test for the fix

---

## Running the Pipeline

### Full Pipeline (Recommended)

```bash
python3 pdf_to_unified_xml.py your_book.pdf --full-pipeline
```

This runs all phases:
1. Creates unified XML with page numbers
2. Derives font roles and extracts TOC
3. Applies heuristics for DocBook structure
4. Packages into deliverable ZIP

### Phase by Phase

```bash
# Phase 1: Create unified XML
python3 pdf_to_unified_xml.py your_book.pdf

# Phase 2: Derive font roles and extract TOC
python3 font_roles_auto.py your_book_unified.xml --out your_book_font_roles.json

# Phase 3: Apply heuristics
python3 heuristics_Nov3.py your_book_unified.xml --font-roles your_book_font_roles.json --out your_book_structured.xml

# Phase 4: Package
python3 create_book_package.py --input your_book_structured.xml --out your_book_package/
```

### Verify TOC.xml

```bash
# Check TOC was extracted
ls -lh *_TOC.xml

# View TOC content
cat your_book_TOC.xml

# Verify font sizes are non-zero
grep 'size="' your_book_TOC.xml
```

---

## Summary

✅ **Problem Identified**: TOC.xml had 0 font size for all entries
✅ **Root Cause Found**: Missing `font_info_map` lookup in `extract_toc_section()`
✅ **Fix Implemented**: Added proper font ID → size lookup
✅ **Tests Passing**: All TOC entries now have correct font sizes
✅ **Pipeline Ready**: TOC.xml can be used for chapter detection and structure analysis

The pipeline is now fully functional with correct font size information throughout!
