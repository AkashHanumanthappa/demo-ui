# Test Plan: Image-Only Pages Fix

## What Changed

Modified `merge_text_and_media_simple()` in `pdf_to_unified_xml.py` to:
- Process pages from BOTH `text_data` and `media_data`
- Handle pages with no text (image-only)
- Estimate HTML dimensions from PyMuPDF dimensions

## Expected Behavior

### Before Fix
```bash
# Page 57 completely missing
grep '<page number="57"' 9780989163286_unified.xml
# (no output)

# Only 598 images
grep '<media id=' 9780989163286_unified.xml | wc -l
# 598
```

### After Fix
```bash
# Page 57 should exist with 2 images
grep -A 10 '<page number="57"' 9780989163286_unified.xml
# Should show:
# <page number="57" width="823.5" height="1161.0">
#   <texts></texts>
#   <media>
#     <media id="p57_img1" ... />
#     <media id="p57_img2" ... />
#   </media>
# </page>

# Should have all 600 images
grep '<media id=' 9780989163286_unified.xml | wc -l
# 600
```

## Test Commands

### 1. Clean previous output
```bash
rm -f 9780989163286_unified.xml 9780989163286_MultiMedia.xml
```

### 2. Run the pipeline
```bash
python3 pdf_to_unified_xml.py 9780989163286.pdf --full-pipeline
```

Watch for console message:
```
⚠ Page 57: No text (image-only page), using estimated dimensions 824x1161
```

### 3. Verify page 57 exists
```bash
# Should show page with 2 images
grep -A 15 '<page number="57"' 9780989163286_unified.xml
```

### 4. Count images
```bash
# MultiMedia.xml
grep '<media id=' 9780989163286_MultiMedia.xml | wc -l
# Should be 600

# unified.xml
grep '<media id=' 9780989163286_unified.xml | wc -l
# Should also be 600 (matching MultiMedia.xml)
```

### 5. Verify the 2 missing images are now present
```bash
# Should find both
grep 'p57_img1' 9780989163286_unified.xml
grep 'p57_img2' 9780989163286_unified.xml
```

### 6. Check coordinates were transformed
```bash
# Should show transformed coordinates (not original PyMuPDF coords)
grep 'p57_img1' 9780989163286_unified.xml
# Original PyMuPDF: x1="85.50" y1="90.0" x2="445.58" y2="324.0"
# Transformed HTML: x1~128, y1~135, x2~668, y2~486
```

### 7. Verify structured XML includes them
```bash
# After running heuristics_Nov3.py
grep 'page57_img' 9780989163286_structured.xml
# Should show <imagedata fileref="MultiMedia/page57_img1.png" />
# and <imagedata fileref="MultiMedia/page57_img2.png" />
```

### 8. Check final package
```bash
# After packaging
unzip -l 9780989163286.zip | grep page57_img
# Should list:
# MultiMedia/page57_img1.png
# MultiMedia/page57_img2.png
```

## What to Look For

### Success Indicators
✅ Console shows "⚠ Page 57: No text (image-only page)" message
✅ Page 57 exists in unified.xml
✅ unified.xml has 600 media elements (same as MultiMedia.xml)
✅ p57_img1 and p57_img2 present in unified.xml
✅ Coordinates are transformed (×1.5 scale factor applied)
✅ Images appear in structured.xml
✅ Images included in final ZIP package

### Failure Indicators
❌ Page 57 still missing
❌ unified.xml still has only 598 images
❌ No warning message about image-only page
❌ Python errors/exceptions during merge

## Common Issues

### If page 57 still missing:
- Check that `pdf_to_unified_xml.py` was saved with changes
- Verify the change is in the `merge_text_and_media_simple()` function
- Look for error messages during merge step

### If coordinates look wrong:
- Check that `transform_media_coords_to_html()` is still being called
- Verify scale factor calculation (should be ~1.5)

### If images not in final package:
- Check that structured XML has the images
- Verify package.py is copying from the right directories
- Check file paths are correct

## Rollback Plan

If the fix causes problems:

```bash
cd /workspace
git diff pdf_to_unified_xml.py
# Review changes

# Revert if needed:
git checkout pdf_to_unified_xml.py
```

## Summary

This fix ensures that **pages with only images (no text) are not skipped** during the merge process. Page 57 in your PDF is a perfect example - it has 2 images but no text, so it was being completely omitted from unified.xml, causing those 2 images to be lost.

The fix processes ALL pages from both text and media data sources, properly handling cases where text is absent.
