# Bug Fixes Summary: Image Handling, Paragraph Building, and Chapter Headers

## Date: November 26, 2025

## Issues Fixed

### 1. Image Filtering Discrepancy (622 → 472 images)

**Problem**: 
- `Multipage_Image_Extractor.py` correctly extracts 622 images to MultiMedia folder
- Final ZIP package only contains 472 images (150 images lost)
- Additional filtering in `package.py` was removing images already filtered by the extractor

**Root Cause**:
- `package.py` was applying classification and filtering logic (`_classify_image()`) that removed:
  - Background images
  - Decorative images without captions
  - Images without labels or captions
- This was DUPLICATE filtering since `Multipage_Image_Extractor.py` already handles all necessary filtering

**Solution** (in `package.py`):
- Changed image filtering bypass logic from `is_epub` only to `bypass_filtering` for BOTH PDF and ePub sources
- Added clear documentation that upstream extractors (Multipage_Image_Extractor.py) already handle filtering
- For PDF sources, ALL images from the extractor are now retained without additional filtering
- Lines modified: 1199-1215, 1409-1410, 1571-1572, 1679-1680

**Result**:
- All 622 images extracted by Multipage_Image_Extractor.py will now be included in the final ZIP
- No duplicate filtering in the pipeline

---

### 2. Aggressive Paragraph Building (Cross-Page Merging)

**Problem**:
- Multiple paragraphs across 2 pages in preface were being clubbed into 1 paragraph
- Paragraphs were spanning page boundaries when they shouldn't

**Root Cause**:
- `group_fragments_into_paragraphs()` in `pdf_to_unified_xml.py` was not checking for page boundaries
- Paragraph gap threshold was too small (1.5x line height)
- Fragments were being merged even when they came from different pages

**Solution** (in `pdf_to_unified_xml.py`):
1. **Added page boundary check** (lines 770-777):
   - Fragments now include `page_num` attribute (line 487)
   - New paragraph always starts at page boundaries
   - Prevents cross-page paragraph merging

2. **Increased paragraph gap threshold** (line 754-756):
   - Changed from 1.5x to 2.0x typical line height
   - Less aggressive paragraph merging
   - Allows for normal line spacing but breaks on clear paragraph gaps

3. **Updated strategy documentation** (line 734):
   - Added "Different page → always new paragraph" as critical rule

**Result**:
- Paragraphs will never span across page boundaries
- Less aggressive merging prevents incorrect paragraph grouping
- Preface paragraphs will now be correctly separated

---

### 3. Multiline Chapter Headers Not Merging

**Problem**:
- In structured XML, multiline chapter headers were not being merged into one full sentence
- Only the first line of a chapter title was being captured

**Root Cause**:
- `_extract_title_from_chapter_content()` in `heuristics_Nov3.py` was only capturing the single block with the largest font
- When chapter titles span multiple lines/blocks, subsequent blocks were ignored

**Solution** (in `heuristics_Nov3.py`):
- Enhanced `_extract_title_from_chapter_content()` to collect consecutive blocks with similar font sizes (lines 1266-1314):
  1. Find the block with the biggest font size
  2. Look forward and backward for consecutive blocks with similar font size (±1pt tolerance)
  3. Check vertical proximity (gap < 2x font size)
  4. Merge all matching blocks into one title string
  5. Join with spaces to create complete sentence

**Features**:
- Font tolerance: 1pt difference allowed for multiline titles
- Vertical proximity check: Gap must be < 2x font size
- Bidirectional search: Checks both forward and backward from the biggest font block
- Debug logging: Shows when multiple blocks are merged

**Result**:
- Multiline chapter headers now merge into complete sentences
- Example: "Chapter 1:\nIntroduction to\nComputer Science" → "Chapter 1: Introduction to Computer Science"

---

## Pipeline Flow Verification (No Duplicate Processing)

### Image Processing Pipeline:
1. **Stage 1**: `Multipage_Image_Extractor.py` - Extract and filter images (622 images)
2. **Stage 2**: `pdf_to_unified_xml.py` - Create unified XML with image references
3. **Stage 3**: `package.py` - Package into ZIP (NOW: bypasses filtering for PDF sources) ✓

### Paragraph Processing Pipeline:
1. **Stage 1**: `pdf_to_excel_columns.py` - Extract text fragments from PDF
2. **Stage 2**: `pdf_to_unified_xml.py::group_fragments_into_paragraphs()` - Group fragments into paragraphs (NOW: respects page boundaries) ✓
3. **Stage 3**: `heuristics_Nov3.py::_finalize_paragraph()` - Finalize paragraph blocks (different stage, no conflict)

### Chapter Header Processing Pipeline:
1. **Stage 1**: PDF bookmark extraction
2. **Stage 2**: `heuristics_Nov3.py::_extract_title_from_chapter_content()` - Extract and merge chapter titles (NOW: merges multiline titles) ✓
3. **Stage 3**: `heuristics_Nov3.py::_inject_bookmark_chapters()` - Inject chapter headings into blocks

**Verification**: No duplicate processing detected. Each function operates at a distinct stage.

---

## Files Modified

1. **`package.py`**: Image filtering bypass for PDF sources (4 changes)
2. **`pdf_to_unified_xml.py`**: Page boundary check and paragraph threshold (3 changes)
3. **`heuristics_Nov3.py`**: Multiline chapter title merging (1 major enhancement)

---

## Testing Recommendations

1. **Image Count Test**:
   - Run full pipeline on a PDF
   - Check MultiMedia folder count after extraction
   - Check final ZIP MultiMedia folder count
   - Verify counts match

2. **Paragraph Boundary Test**:
   - Process a PDF with preface spanning 2+ pages
   - Verify paragraphs don't span across pages
   - Check XML for page boundary markers in paragraphs

3. **Chapter Title Test**:
   - Process a PDF with multiline chapter titles
   - Check structured XML chapter titles
   - Verify all lines of title are merged

---

## Expected Behavior After Fixes

✓ All 622 images from Multipage_Image_Extractor.py appear in final ZIP  
✓ Paragraphs never span page boundaries  
✓ Less aggressive paragraph merging (2.0x threshold instead of 1.5x)  
✓ Multiline chapter headers merge into complete sentences  
✓ No duplicate processing in the pipeline  

---

## Notes

- The `bypass_filtering` flag in `package.py` now applies to both PDF and ePub sources
- Page tracking (`page_num`) is now added to all text fragments during merge
- Chapter title merging uses ±1pt font tolerance and vertical proximity checks
- All changes are backward compatible with existing pipeline
