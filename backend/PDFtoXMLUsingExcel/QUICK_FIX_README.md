# Quick Fix: Reference Mapper Empty Issue

## Problem

- `_reference_mapping.json` shows all zeros
- Images from `MultiMedia.xml` not transferring to chapter XMLs
- Empty `<media />` tags in `_unified.xml` (this is actually EXPECTED - they're placeholders!)

## Root Cause

The reference mapper (which tracks image name transformations) was never initialized in the PDF pipeline, so no images were registered.

## Solution Applied

Three changes to fix the issue:

### 1. `pdf_to_unified_xml.py` - Initialize mapper at start

```python
# Added:
from reference_mapper import get_mapper, reset_mapper

# In process_pdf_to_unified_xml():
reset_mapper()  # Initialize clean mapper
```

### 2. `pdf_to_unified_xml.py` - Export mapping after Phase 1

```python
# At end of process_pdf_to_unified_xml():
mapper.export_to_json(Path(f"{base_name}_reference_mapping_phase1.json"))
```

### 3. `package.py` - Load mapping before packaging

```python
# At start of package_docbook():
mapper.import_from_json(mapping_file)  # Restore mapper state
```

## Verify The Fix Works

### Step 1: Run pipeline

```bash
python pdf_to_unified_xml.py your-document.pdf --full-pipeline
```

### Step 2: Check console output

You should see:
```
✓ Reference mapper initialized for image tracking
...
✓ Reference mapping exported: your-document_reference_mapping_phase1.json
...
✓ Loaded reference mapping: your-document_reference_mapping_phase1.json
   - 997 images tracked
```

### Step 3: Verify mapping file

```bash
python verify_reference_mapper.py your-document
```

Should show:
```
✅ Mapper has 997 resources!
```

### Step 4: Check final package

```bash
unzip -l your-document.zip | grep "MultiMedia.*\.jpg" | wc -l
```

Should show the number of images (e.g., 997).

## What Changed

**BEFORE (broken):**
- Mapper never initialized
- Images not registered during extraction
- Mapper empty during packaging
- Images not found/copied to chapters
- Result: Empty images in final package

**AFTER (fixed):**
- Mapper initialized at pipeline start ✅
- Images registered during extraction ✅
- Mapper exported to JSON after Phase 1 ✅
- Mapper loaded from JSON before packaging ✅
- Images found and copied to chapters ✅
- Result: All images in final package ✅

## Key Files Modified

- ✅ `pdf_to_unified_xml.py` - Import, initialize, export mapper
- ✅ `package.py` - Load mapper from JSON

## Key Files Created

- ✅ `REFERENCE_MAPPER_FIX_SUMMARY.md` - Detailed explanation
- ✅ `verify_reference_mapper.py` - Verification tool
- ✅ `diagnose_empty_media_tables.py` - Diagnostic tool

## Understanding Empty `<media />` Tags

**This is EXPECTED behavior!**

The `_unified.xml` file contains **placeholders** for media:

```xml
<!-- _unified.xml (Phase 1) - EXPECTED -->
<page>
  <media>
    <media reading_order="5.5" x1="100" y1="200" x2="400" y2="500"/>
  </media>
</page>
```

These are converted to actual DocBook elements later:

```xml
<!-- structured.xml (Phase 2) -->
<figure>
  <mediaobject>
    <imagedata fileref="MultiMedia/img_001.png"/>
  </mediaobject>
</figure>
```

And finally renamed in the package:

```xml
<!-- ch0001.xml in ZIP (Phase 3) -->
<figure>
  <mediaobject>
    <imagedata fileref="MultiMedia/Ch0001f01.jpg"/>
  </mediaobject>
</figure>
```

## Troubleshooting

### If mapper still shows 0 resources:

1. **Check import works:**
   ```bash
   python3 -c "from reference_mapper import get_mapper; print('OK')"
   ```

2. **Check Multipage_Image_Extractor.py can import it:**
   ```bash
   python3 -c "from Multipage_Image_Extractor import extract_media_and_tables; print('OK')"
   ```

3. **Check for error messages:**
   ```bash
   python pdf_to_unified_xml.py your.pdf 2>&1 | grep -i "reference\|mapper\|warning"
   ```

### If images still missing from chapters:

1. **Check Phase 1 mapping exists:**
   ```bash
   ls -lh *_reference_mapping_phase1.json
   ```

2. **Check mapper was loaded:**
   ```bash
   # Look for this line in output:
   # ✓ Loaded reference mapping: your-document_reference_mapping_phase1.json
   ```

3. **Check MultiMedia folder exists:**
   ```bash
   ls -lh your-document_MultiMedia/ | head -20
   ```

4. **Check media fetcher can find images:**
   ```bash
   # Look for warnings about missing media in output
   grep -i "missing media\|could not find" output.log
   ```

## Next Steps

1. ✅ Re-run pipeline on your PDF
2. ✅ Verify mapper populated (use `verify_reference_mapper.py`)
3. ✅ Check final package has images
4. ✅ Validate chapter XMLs reference correct images

## Support

If issues persist after applying the fix:

1. Run diagnostic: `python diagnose_empty_media_tables.py <base_name>`
2. Run verification: `python verify_reference_mapper.py <base_name>`
3. Check the detailed guide: `REFERENCE_MAPPER_FIX_SUMMARY.md`
4. Share the output from both diagnostic tools
